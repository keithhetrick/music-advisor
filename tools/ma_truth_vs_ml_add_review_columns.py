#!/usr/bin/env python
"""
ma_truth_vs_ml_add_review_columns.py

Add / normalize human-review columns for ENERGY and DANCE truth bands.

This script is meant to be run on the *triage* CSV, but it will work
on any CSV that at least has:

    - energy_truth   (lo/mid/hi)
    - dance_truth    (lo/mid/hi)

It will ensure the following columns exist:

    energy_truth_reviewed        (yes/no)
    energy_truth_corrected_band  (lo/mid/hi or "")
    energy_truth_final_band      (lo/mid/hi)

    dance_truth_reviewed         (yes/no)
    dance_truth_corrected_band   (lo/mid/hi or "")
    dance_truth_final_band       (lo/mid/hi)

Logic for *_final_band:

    If *_truth_corrected_band in {lo, mid, hi}:
        *_truth_final_band = corrected_band
        *_truth_reviewed   = "yes"
    else:
        *_truth_final_band = *_truth

You can safely re-run this script after editing the CSV in Excel/Sheets:
it will preserve any corrections you’ve already made and just normalize
the values.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


AXES = ["energy", "dance"]


def normalize_yes_no(v: str) -> str:
    if not v:
        return "no"
    v = v.strip().lower()
    if v in {"y", "yes", "1", "true"}:
        return "yes"
    if v in {"n", "no", "0", "false"}:
        return "no"
    # default to "yes" if they typed something weird but non-empty
    return "yes"


def normalize_band(v: str) -> str:
    if not v:
        return ""
    v = v.strip().lower()
    if v in {"lo", "low"}:
        return "lo"
    if v in {"mid", "medium", "med"}:
        return "mid"
    if v in {"hi", "high"}:
        return "hi"
    # unknown band -> treat as blank so we fall back to original truth
    return ""


def add_review_columns(
    in_csv: Path,
    out_csv: Path,
) -> None:
    with in_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = list(reader)
        fieldnames = list(reader.fieldnames or [])

    # Ensure required base columns exist
    for axis in AXES:
        truth_col = f"{axis}_truth"
        if truth_col not in fieldnames:
            raise ValueError(f"Missing required column: {truth_col}")

    # Ensure review columns exist
    for axis in AXES:
        reviewed_col = f"{axis}_truth_reviewed"
        corrected_col = f"{axis}_truth_corrected_band"
        final_col = f"{axis}_truth_final_band"

        for col in (reviewed_col, corrected_col, final_col):
            if col not in fieldnames:
                fieldnames.append(col)

    # Process rows
    new_rows: List[Dict[str, str]] = []
    for row in rows:
        for axis in AXES:
            truth_col = f"{axis}_truth"
            reviewed_col = f"{axis}_truth_reviewed"
            corrected_col = f"{axis}_truth_corrected_band"
            final_col = f"{axis}_truth_final_band"

            truth = (row.get(truth_col) or "").strip().lower()

            # Existing values (if any)
            reviewed_raw = row.get(reviewed_col) or ""
            corrected_raw = row.get(corrected_col) or ""

            reviewed = normalize_yes_no(reviewed_raw)
            corrected = normalize_band(corrected_raw)

            if corrected in {"lo", "mid", "hi"}:
                # Use corrected band as final
                final = corrected
                reviewed = "yes"
            else:
                # Fall back to original truth band
                final = truth

            row[reviewed_col] = reviewed
            row[corrected_col] = corrected
            row[final_col] = final

        new_rows.append(row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)

    print(f"[OK] Wrote with review columns to {out_csv}")
    print("Columns added/normalized:")
    for axis in AXES:
        print(
            f"  - {axis}_truth_reviewed, "
            f"{axis}_truth_corrected_band, "
            f"{axis}_truth_final_band"
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--csv",
        required=True,
        help="Input CSV (e.g. calibration/aee_ml_reports/truth_vs_ml_triage_v1_1.csv)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output CSV with review columns added/normalized",
    )
    args = ap.parse_args()

    in_csv = Path(args.csv)
    out_csv = Path(args.out)

    add_review_columns(in_csv=in_csv, out_csv=out_csv)


if __name__ == "__main__":
    main()
