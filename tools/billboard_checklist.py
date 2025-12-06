#!/usr/bin/env python3
"""
Produce a procurement checklist from the UT Billboard export CSV.

Usage:
  python tools/billboard_checklist.py --csv <DATA_ROOT>/market_norms/raw/hot100_top40_2025_11.csv

Outputs a CSV with an added "status" column for tracking audio acquisition.
"""

from __future__ import annotations

import argparse
import pandas as pd
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Create a procurement checklist CSV.")
    ap.add_argument("--csv", required=True, help="Input chart CSV (e.g., hot100_top40_2025_11.csv)")
    ap.add_argument("--out", help="Output path (defaults to adding _checklist.csv)")
    args = ap.parse_args()

    src = Path(args.csv)
    out = Path(args.out) if args.out else src.with_name(src.stem + "_checklist.csv")

    df = pd.read_csv(src)
    if "status" not in df.columns:
        df["status"] = ""
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"[billboard_checklist] wrote checklist -> {out} ({len(df)} rows)")


if __name__ == "__main__":
    main()
