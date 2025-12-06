#!/usr/bin/env python
"""
ma_truth_vs_ml_triage.py

Given a truth_vs_ml CSV that also includes feature-derived bands
(e.g. from ma_apply_axis_bands_from_thresholds.py), this script
groups songs into simple "who agrees with whom?" buckets to help
diagnose where problems really are.

Expected columns:

    energy_truth          (str: "lo" | "mid" | "hi")
    energy_ml             (str)
    energy_feature_band   (str)

    dance_truth
    dance_ml
    dance_feature_band

It prints summary counts and optionally writes a triage CSV with
a "triage_tag_*" column for each axis.
"""

import argparse
import csv
from collections import Counter
from typing import Dict, List


def triage_axis(row, truth_col, ml_col, feat_col):
    truth = (row.get(truth_col, "") or "").strip()
    ml = (row.get(ml_col, "") or "").strip()
    feat = (row.get(feat_col, "") or "").strip()

    # Basic sanity: if any is missing, tag as 'missing'
    if not truth or not ml or not feat:
        return "missing"

    # All three agree
    if truth == ml == feat:
        return "all_agree"

    # Truth & ML agree, feature disagrees
    if truth == ml != feat:
        return "truth_ml_agree_feat_diff"

    # Truth & feature agree, ML disagrees
    if truth == feat != ml:
        return "truth_feat_agree_ml_diff"

    # ML & feature agree, truth disagrees
    if ml == feat != truth:
        return "ml_feat_agree_truth_diff"

    # All three different
    return "all_disagree"


def process_csv(in_csv: str, out_csv: str = None) -> None:
    with open(in_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = list(reader)

    if not rows:
        print("[WARN] No rows found in CSV.")
        return

    # Axis column name triples: (truth, ml, feature_band)
    axes = {
        "energy": (
            "energy_truth",
            "energy_ml",
            "energy_feature_band",
        ),
        "dance": (
            "dance_truth",
            "dance_ml",
            "danceability_feature_band",  # <<— this was wrong before
        ),
    }

    # Tally per axis
    tallies: Dict[str, Counter] = {axis: Counter() for axis in axes}
    # Store per-row tags for output
    for row in rows:
        for axis, (truth_col, ml_col, feat_col) in axes.items():
            tag = triage_axis(row, truth_col, ml_col, feat_col)
            tallies[axis][tag] += 1
            row[f"triage_tag_{axis}"] = tag

    n_total = len(rows)
    print(f"Total rows: {n_total}\n")
    for axis in axes:
        print(f"=== {axis.upper()} triage ===")
        for tag, count in tallies[axis].most_common():
            pct = 100.0 * count / max(n_total, 1)
            print(f"{tag:30s}: {count:4d} ({pct:5.1f}%)")
        print()

    # Optional CSV output with triage tags
    if out_csv:
        fieldnames = list(rows[0].keys())
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[OK] Wrote triage CSV to {out_csv}")


def main():
    parser = argparse.ArgumentParser(
        description="Triage disagreements between truth / ML / feature-derived bands."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Input CSV with energy_*/dance_* truth, ml, and *_feature_band columns.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional path to write a triage CSV with triage_tag_* columns.",
    )
    args = parser.parse_args()
    process_csv(in_csv=args.csv, out_csv=args.out)


if __name__ == "__main__":
    main()
