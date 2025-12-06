#!/usr/bin/env python3
"""
Compare chart CSV vs features CSV and report missing tracks.

Usage:
  python tools/missing_features_report.py \
    --chart <DATA_ROOT>/market_norms/raw/hot100_top40_2025_11.csv \
    --features <DATA_ROOT>/market_norms/raw/hot100_top40_2025_11_features.csv
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main() -> None:
    ap = argparse.ArgumentParser(description="Report which chart titles are missing features.")
    ap.add_argument("--chart", required=True, help="Chart CSV with title/artist/chart_date/rank.")
    ap.add_argument("--features", required=True, help="Features CSV produced by adapter.")
    args = ap.parse_args()

    chart = pd.read_csv(args.chart)
    feats = pd.read_csv(args.features) if Path(args.features).exists() else pd.DataFrame(columns=["title"])

    chart["key"] = chart["title"].fillna("").map(norm)
    feats["key"] = feats["title"].fillna("").map(norm)

    missing = chart[~chart["key"].isin(set(feats["key"]))]
    print(f"Chart rows: {len(chart)}, Features rows: {len(feats)}, Missing: {len(missing)}")
    if not missing.empty:
        print(missing[["chart_date", "rank", "title", "artist"]].head(20).to_string(index=False))
        out = Path(args.features).with_name(Path(args.features).stem + "_missing.csv")
        missing.to_csv(out, index=False)
        print(f"Missing rows written to {out}")


if __name__ == "__main__":
    main()
