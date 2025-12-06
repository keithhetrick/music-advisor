#!/usr/bin/env python3
"""
Compute procurement progress from a checklist CSV with a 'status' column.

Accepted status values for "done": any case-insensitive entry starting with 'done', 'yes', 'ok', 'y', 'complete'.
Anything else counts as pending.

Usage:
  python tools/procurement_progress.py --csv <DATA_ROOT>/market_norms/raw/hot100_top40_2025_Q4_checklist.csv
"""
from __future__ import annotations

import argparse
import pandas as pd
from pathlib import Path


def is_done(val: str) -> bool:
    if not isinstance(val, str):
        return False
    v = val.strip().lower()
    return v.startswith(("done", "yes", "y", "ok", "complete"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute procurement progress.")
    ap.add_argument("--csv", required=True, help="Checklist CSV with 'status' column.")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    if "status" not in df.columns:
        print("No status column found.")
        return
    done = df["status"].apply(is_done)
    total = len(df)
    completed = done.sum()
    pct = (completed / total * 100.0) if total else 0.0
    print(f"[procurement_progress] {completed}/{total} ({pct:.1f}%) complete")

    if completed < total:
        missing = df[~done][["chart_date", "rank", "title", "artist"]].head(10)
        print("Example pending rows:")
        print(missing.to_string(index=False))


if __name__ == "__main__":
    main()
