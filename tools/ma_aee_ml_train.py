#!/usr/bin/env python3
# tools/ma_aee_ml_train.py
"""
Train lightweight ML models for Energy & Danceability axis calibration.

This script is a thin CLI wrapper around the aee_ml package. It:

- Reads:
    - calibration/benchmark_truth.csv
    - *.features.json under a given root (e.g. features_output/)
- Uses aee_ml.datasets + aee_ml.models to build X, y and train logistic models.
- Writes:
    - calibration/aee_ml/axis_energy.pkl
    - calibration/aee_ml/axis_dance.pkl
    - calibration/aee_ml/aee_ml_manifest.json

It NEVER modifies existing *.features.json or *.hci.json schemas.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()


from aee_ml import (
    AEE_ML_VERSION,
    AXIS_FEATURE_KEYS,
    BAND_TO_IDX,
    build_supervised_records,
    design_matrix,
    train_axis_model,
)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train ML calibration models for Energy and Danceability axes."
    )
    p.add_argument(
        "--truth",
        required=True,
        help="Path to calibration/benchmark_truth.csv",
    )
    p.add_argument(
        "--root",
        required=True,
        help="Root directory containing *.features.json files (e.g. features_output)",
    )
    p.add_argument(
        "--out-dir",
        default="calibration/aee_ml",
        help="Directory where trained models & manifest will be written.",
    )
    p.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data to reserve for test accuracy (default 0.2).",
    )
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    truth_csv = Path(args.truth).expanduser().resolve()
    features_root = Path(args.root).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not truth_csv.is_file():
        sys.stderr.write(f"[ma_aee_ml_train] ERROR: truth CSV not found: {truth_csv}\n")
        return 1
    if not features_root.exists():
        sys.stderr.write(
            f"[ma_aee_ml_train] ERROR: features root does not exist: {features_root}\n"
        )
        return 1

    records, missing = build_supervised_records(truth_csv, features_root)
    if missing:
        sys.stderr.write(
            "[ma_aee_ml_train] WARNING: no *.features.json found for: "
            + ", ".join(sorted(set(missing)))
            + "\n"
        )

    if not records:
        sys.stderr.write(
            "[ma_aee_ml_train] ERROR: no usable records after joining truth+features.\n"
        )
        return 1

    X, y_energy, y_dance = design_matrix(records)

    from aee_ml import AxisReport  # just for type hints / clarity

    energy_model, energy_report = train_axis_model(
        "energy", X, y_energy, test_size=args.test_size
    )
    dance_model, dance_report = train_axis_model(
        "dance", X, y_dance, test_size=args.test_size
    )

    # Persist models
    import pickle

    energy_path = out_dir / "axis_energy.pkl"
    dance_path = out_dir / "axis_dance.pkl"

    with energy_path.open("wb") as f:
        pickle.dump(energy_model, f)
    with dance_path.open("wb") as f:
        pickle.dump(dance_model, f)

    # Build manifest for auditability
    manifest = {
        "aee_ml_version": AEE_ML_VERSION,
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "truth_csv": str(truth_csv),
        "features_root": str(features_root),
        "feature_keys": list(AXIS_FEATURE_KEYS),
        "n_records": len(records),
        "missing_audio_names": sorted(set(missing)),
        "axis_reports": {
            "energy": energy_report.__dict__,
            "dance": dance_report.__dict__,
        },
        "band_encoding": BAND_TO_IDX,
    }

    manifest_path = out_dir / "aee_ml_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    # Small human-readable summary
    print("[ma_aee_ml_train] Trained ML calibration models:")
    print(f"  Records used: {len(records)}")
    print(f"  Feature keys: {', '.join(AXIS_FEATURE_KEYS)}")
    print("  Energy axis:")
    print(
        f"    train_acc = {energy_report.train_acc:.3f}, "
        f"test_acc = {energy_report.test_acc:.3f}, "
        f"n_train = {energy_report.n_train}, n_test = {energy_report.n_test}, "
        f"bands = {energy_report.bands_present}"
    )
    print("  Danceability axis:")
    print(
        f"    train_acc = {dance_report.train_acc:.3f}, "
        f"test_acc = {dance_report.test_acc:.3f}, "
        f"n_train = {dance_report.n_train}, n_test = {dance_report.n_test}, "
        f"bands = {dance_report.bands_present}"
    )
    print(f"  Saved models to: {energy_path} and {dance_path}")
    print(f"  Manifest: {manifest_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
