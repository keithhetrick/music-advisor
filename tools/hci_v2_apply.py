#!/usr/bin/env python
"""
hci_v2_apply.py

Apply a trained HCI_audio_v2 model to .hci.json files under one or more roots.

For each .hci.json:
  - Reads the `audio_axes` dict.
  - Builds a feature vector in the order used at training time.
  - Predicts EchoTarget_v2_hat using the trained model.
  - Clamps to [0.0, 1.0].
  - Writes/updates:

    "HCI_audio_v2": {
      "raw": <float>,    # model prediction
      "score": <float>,  # currently same as raw (no extra calibration)
      "meta": {
        "model_id": "...",
        "feature_cols": [...],
        "train_csv": "...",
        "val_r2": ...,
        "val_mae": ...
      }
    }

This does NOT touch HCI_v1 fields; final fusion is still handled by
hci_final_score.py.
"""

import argparse
import json
import os
from typing import Any, Dict, List

from shared.config.paths import (
    get_audio_hci_v2_model_meta_path,
    get_audio_hci_v2_model_path,
)

try:
    import joblib
except ImportError as e:
    raise SystemExit(
        "joblib is required for hci_v2_apply.py. "
        "Install it in your venv with:\n\n"
        "  pip install joblib\n"
    ) from e


def _log(msg: str) -> None:
    print(f"[INFO] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _err(msg: str) -> None:
    print(f"[ERROR] {msg}")


def load_model_and_meta(model_path: str, meta_path: str):
    if not os.path.exists(model_path):
        _err(f"Model file not found: {model_path}")
        raise SystemExit(1)
    if not os.path.exists(meta_path):
        _err(f"Meta JSON not found: {meta_path}")
        raise SystemExit(1)

    _log(f"Loading model from {model_path}")
    model = joblib.load(model_path)

    _log(f"Loading meta from {meta_path}")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    feature_cols = meta.get("feature_cols")
    if not feature_cols:
        _err("Meta JSON is missing 'feature_cols'; cannot apply model.")
        raise SystemExit(1)

    return model, meta, feature_cols


def find_hci_files(roots: List[str]) -> List[str]:
    hci_files: List[str] = []
    for root in roots:
        if not os.path.isdir(root):
            _warn(f"Root is not a directory; skipping: {root}")
            continue
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if not name.endswith(".hci.json"):
                    continue
                hci_files.append(os.path.join(dirpath, name))
    return hci_files


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)


def extract_features_from_axes(
    audio_axes: Any,
    feature_cols: List[str],
) -> List[float]:
    """
    Build a feature vector from the audio_axes dict, in the same order
    as training. If a feature is missing, default to 0.0.
    """
    if not isinstance(audio_axes, dict):
        # Legacy list format or bad data: fallback to zeros.
        return [0.0 for _ in feature_cols]

    vec: List[float] = []
    for key in feature_cols:
        v = audio_axes.get(key)
        if v is None:
            vec.append(0.0)
        else:
            try:
                vec.append(float(v))
            except ValueError:
                vec.append(0.0)
    return vec


def apply_model_to_file(
    path: str,
    model,
    meta: Dict[str, Any],
    feature_cols: List[str],
    dry_run: bool = False,
) -> bool:
    """
    Return True if file was updated, False otherwise.
    """
    try:
        data = load_json(path)
    except Exception as e:
        _warn(f"Failed to read JSON from {path}: {e}")
        return False

    audio_axes = data.get("audio_axes")
    if audio_axes is None:
        _warn(f"No audio_axes in {os.path.basename(path)}; skipping.")
        return False

    x_vec = extract_features_from_axes(audio_axes, feature_cols)
    import numpy as np

    X = np.array([x_vec], dtype=float)
    y_hat = float(model.predict(X)[0])

    # Clamp to [0, 1] since labels are 0–1
    if y_hat < 0.0:
        y_hat = 0.0
    elif y_hat > 1.0:
        y_hat = 1.0

    hci_audio_v2 = data.get("HCI_audio_v2", {})
    hci_audio_v2["raw"] = y_hat
    hci_audio_v2["score"] = y_hat

    # Slim meta block for traceability
    hci_meta = hci_audio_v2.get("meta", {})
    hci_meta["model_id"] = meta.get("hci_audio_v2_version", "pop_us_2025Q4_v1")
    hci_meta["feature_cols"] = feature_cols
    hci_meta["train_csv"] = meta.get("train_csv")
    metrics = meta.get("metrics", {})
    if metrics:
        hci_meta["val_r2"] = metrics.get("val_r2")
        hci_meta["val_mae"] = metrics.get("val_mae")
        hci_meta["n_samples"] = metrics.get("n_samples")
    hci_audio_v2["meta"] = hci_meta

    data["HCI_audio_v2"] = hci_audio_v2

    if dry_run:
        _log(f"[DRY-RUN] Would update HCI_audio_v2 for {path}")
        return False

    save_json(path, data)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply trained HCI_audio_v2 model to .hci.json files."
    )
    parser.add_argument(
        "--root",
        action="append",
        required=True,
        help="Root directory containing .hci.json files (can be given multiple times).",
    )
    parser.add_argument(
        "--model",
        default=str(get_audio_hci_v2_model_path()),
        help=f"Path to trained model (default: {get_audio_hci_v2_model_path()})",
    )
    parser.add_argument(
        "--meta",
        default=str(get_audio_hci_v2_model_meta_path()),
        help=f"Path to model meta JSON (default: {get_audio_hci_v2_model_meta_path()})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, do not write changes; just log what would happen.",
    )

    args = parser.parse_args()

    model, meta, feature_cols = load_model_and_meta(args.model, args.meta)
    roots = [os.path.abspath(r) for r in args.root]
    hci_files = find_hci_files(roots)

    _log(f"Found {len(hci_files)} .hci.json file(s) under roots: {', '.join(roots)}")

    updated = 0
    for path in hci_files:
        if apply_model_to_file(path, model, meta, feature_cols, dry_run=args.dry_run):
            updated += 1

    _log(f"DONE. Updated {updated} file(s).")


if __name__ == "__main__":
    main()
