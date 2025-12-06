#!/usr/bin/env python3
# tools/ma_aee_ml_apply.py
"""
Apply trained ML calibration models to *.features.json files.

This is a thin CLI wrapper around aee_ml.apply. It:

- Loads models trained by ma_aee_ml_train.py from calibration/aee_ml/.
- Walks a --root directory of *.features.json files.
- For each file, builds the feature vector and predicts:
    - Energy axis: band + continuous value + probs
    - Danceability axis: band + continuous value + probs
- Writes a sidecar JSON per input file into --out-dir:

    features_output/2020_the_weeknd__blinding_lights__album.features.json
        → calibration/aee_ml_outputs/2020_the_weeknd__blinding_lights__album.ml_axes.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()


from aee_ml import (
    AEE_ML_VERSION,
    axis_from_model,
    iter_features_json,
    load_features,
    load_manifest,
    load_models,
    make_feature_vector,
)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Apply trained AEE ML calibration models to features."
    )
    p.add_argument(
        "--root",
        required=True,
        help="Root directory containing *.features.json files (e.g. features_output)",
    )
    p.add_argument(
        "--model-dir",
        default="calibration/aee_ml",
        help="Directory where axis_*.pkl and aee_ml_manifest.json live.",
    )
    p.add_argument(
        "--out-dir",
        default="calibration/aee_ml_outputs",
        help="Directory for *.ml_axes.json sidecar outputs.",
    )
    p.add_argument(
        "--mode",
        default="ml_calibrated",
        choices=["ml_calibrated", "baseline"],
        help=(
            "Tag to write into the output meta. 'baseline' does not change behavior, "
            "but makes it easy to compare future modes."
        ),
    )
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    model_dir = Path(args.model_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()

    if not root.exists():
        sys.stderr.write(
            f"[ma_aee_ml_apply] ERROR: features root does not exist: {root}\n"
        )
        return 1
    if not model_dir.exists():
        sys.stderr.write(
            f"[ma_aee_ml_apply] ERROR: model dir does not exist: {model_dir}\n"
        )
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        manifest = load_manifest(model_dir)
    except Exception as exc:
        sys.stderr.write(f"[ma_aee_ml_apply] ERROR loading manifest: {exc}\n")
        return 1

    feature_keys = manifest.get("feature_keys")

    try:
        energy_model, dance_model = load_models(model_dir)
    except Exception as exc:
        sys.stderr.write(f"[ma_aee_ml_apply] ERROR loading models: {exc}\n")
        return 1

    feature_paths = iter_features_json(root)
    if not feature_paths:
        sys.stderr.write(
            f"[ma_aee_ml_apply] WARNING: no *.features.json files found under {root}\n"
        )
        return 0

    print(
        f"[ma_aee_ml_apply] Applying ML models to {len(feature_paths)} feature files "
        f"using feature_keys={feature_keys or 'default AXIS_FEATURE_KEYS'}"
    )

    for path in feature_paths:
        feats = load_features(path)
        feat_vec = make_feature_vector(feats, feature_keys=feature_keys)

        energy_axis = axis_from_model(energy_model, feat_vec)
        dance_axis = axis_from_model(dance_model, feat_vec)

        audio_name = feats.get("audio_name") or path.stem.replace(".features", "")

        out_obj: Dict[str, Any] = {
            "audio_name": audio_name,
            "source_features_path": str(path),
            "mode": args.mode,
            "axes_ml": {
                "Energy": energy_axis,
                "Danceability": dance_axis,
            },
            "meta": {
                "aee_ml_version": manifest.get("aee_ml_version", AEE_ML_VERSION),
                "created_from_manifest": manifest.get("created_utc"),
                "truth_csv": manifest.get("truth_csv"),
                "features_root_for_training": manifest.get("features_root"),
            },
        }

        out_path = out_dir / f"{path.stem}.ml_axes.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(out_obj, f, indent=2, sort_keys=True)

    print(
        f"[ma_aee_ml_apply] Wrote ML axis sidecars to {out_dir} "
        "(one *.ml_axes.json per *.features.json)."
    )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
