#!/usr/bin/env python3
"""
Export a slice of the Billboard DB by date range and optional top_k.

Examples:
  # Q4 2025 Hot 100, top 40
  python tools/export_billboard_slice.py \
    --db <DATA_ROOT>/market_norms/market_norms_billboard.db \
    --chart hot100 \
    --start 2025-10-01 --end 2025-12-31 \
    --top-k 40 \
    --out <DATA_ROOT>/market_norms/raw/hot100_top40_2025_Q4.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
from tools.market_norms_queries import get_month_charts


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Export chart slice from Billboard DB.")
    ap.add_argument("--db", required=True, help="Path to market_norms_billboard.db")
    ap.add_argument("--chart", choices=["hot100", "bb200"], required=True, help="Chart to export")
    ap.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    ap.add_argument("--top-k", type=int, default=None, help="Optional rank cutoff (e.g., 40)")
    ap.add_argument("--out", required=True, help="Output CSV path")
    return ap.parse_args()


def daterange_months(start: pd.Timestamp, end: pd.Timestamp):
    months = []
    cur = pd.Timestamp(start.year, start.month, 1)
    last = pd.Timestamp(end.year, end.month, 1)
    while cur <= last:
        months.append((cur.year, cur.month))
        cur = (cur + pd.offsets.MonthBegin(1))
    return months


def main() -> None:
    args = parse_args()
    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end)

    frames = []
    for y, m in daterange_months(start, end):
        df = get_month_charts(args.chart, y, m, top_k=args.top_k, db=args.db)
        if df.empty:
            continue
        df = df[(df["chart_date"] >= start) & (df["chart_date"] <= end)]
        frames.append(df)

    out_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"[export_billboard_slice] wrote {len(out_df)} rows -> {out_path}")


if __name__ == "__main__":
    main()
