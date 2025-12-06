#!/usr/bin/env python3
"""
ma_truth_vs_ml_export_buckets.py

Given a triage CSV from ma_truth_vs_ml_triage.py, split rows into
separate CSVs per axis (energy/dance) and per triage bucket.

Example:
    python tools/ma_truth_vs_ml_export_buckets.py \
      --csv calibration/aee_ml_reports/truth_vs_ml_triage_v1_1.csv
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def slugify_bucket(name: str) -> str:
    """
    Turn triage bucket labels like 'truth_feat_agree_ml_diff'
    into safe filename fragments.
    """
    return name.strip().replace(" ", "_")


def find_triage_cols(fieldnames):
    """
    Try to auto-detect triage columns in a forgiving way.
    We expect something like:
      - energy_triage
      - dance_triage
      - energy_triage_tag
      - dance_triage_tag
    but we'll accept any column that contains 'triage'.
    """
    candidates = [c for c in fieldnames if "triage" in c.lower()]

    if not candidates:
        # Helpful debug print so we can see what's actually in the file
        print("[ERROR] No triage columns found. Fieldnames were:")
        for fn in fieldnames:
            print(f"  - {fn}")
        raise ValueError(
            "No triage-related columns found in CSV. "
            "Did you run ma_truth_vs_ml_triage.py first?"
        )

    print("[INFO] Detected triage columns:")
    for c in candidates:
        print(f"  - {c}")

    return candidates


def axis_name_from_triage_col(col: str) -> str:
    """
    Derive axis name from triage column, e.g.:
      'energy_triage' -> 'energy'
      'dance_triage_tag' -> 'dance'
    """
    # strip the first '_triage...' suffix
    lower = col.lower()
    idx = lower.find("_triage")
    if idx != -1:
        return col[:idx]
    # fallback: just strip trailing '_tag' if present
    if lower.endswith("_tag"):
        return col[:-4]
    return col


def export_buckets(in_csv: Path) -> None:
    if not in_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {in_csv}")

    out_dir = in_csv.parent
    base = in_csv.stem  # e.g., "truth_vs_ml_triage_v1_1"

    with in_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not rows:
        print(f"[WARN] No rows found in {in_csv}")
        return

    triage_cols = find_triage_cols(fieldnames)

    # Gather buckets per axis
    buckets: Dict[str, Dict[str, List[dict]]] = {}
    for axis_triage_col in triage_cols:
        axis = axis_name_from_triage_col(axis_triage_col)
        if axis not in buckets:
            buckets[axis] = {}

    for row in rows:
        for axis_triage_col in triage_cols:
            axis = axis_name_from_triage_col(axis_triage_col)
            tag = (row.get(axis_triage_col) or "").strip()
            if not tag:
                tag = "missing"
            if tag not in buckets[axis]:
                buckets[axis][tag] = []
            buckets[axis][tag].append(row)

    # Write per-axis, per-bucket CSVs
    for axis, axis_buckets in buckets.items():
        print(f"\n=== {axis.upper()} buckets ===")
        for tag, bucket_rows in axis_buckets.items():
            slug = slugify_bucket(tag)
            out_path = out_dir / f"{base}__{axis}_{slug}.csv"
            with out_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(bucket_rows)
            print(f"  {tag:30s}: {len(bucket_rows):4d} rows -> {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split truth_vs_ml triage CSV into per-axis, per-bucket CSVs."
    )
    parser.add_argument(
        "--csv",
        type=str,
        required=True,
        help="Path to triage CSV (output of ma_truth_vs_ml_triage.py)",
    )
    args = parser.parse_args()

    in_csv = Path(args.csv)
    export_buckets(in_csv)


if __name__ == "__main__":
    main()
