#!/usr/bin/env python3
"""
Export top-40 rows from the UT Billboard SQLite DB to a CSV for downstream
audio-feature enrichment.

Examples:
  python tools/export_billboard_top40.py --db <DATA_ROOT>/market_norms/market_norms_billboard.db \\
      --chart hot100 --year 2025 --month 11 --out /tmp/hot100_top40_2025_11.csv

  python tools/export_billboard_top40.py --db <DATA_ROOT>/market_norms/market_norms_billboard.db \\
      --chart bb200 --chart-date 2025-11-29 --out /tmp/bb200_top40_2025-11-29.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tools.market_norms_queries import (
    get_top40_for_month,
    get_top40_for_week,
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Export Top 40 from UT Billboard DB to CSV.")
    ap.add_argument("--db", required=True, help="Path to market_norms_billboard.db")
    ap.add_argument("--chart", choices=["hot100", "bb200"], required=True, help="Chart to export.")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--chart-date", help="Specific chart_date (YYYY-MM-DD) to export.")
    group.add_argument("--year-month", nargs=2, metavar=("YEAR", "MONTH"), help="Year and month, e.g. 2025 11.")
    ap.add_argument("--out", required=True, help="Output CSV path.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).resolve()
    out_path = Path(args.out).resolve()

    if args.chart_date:
        df = get_top40_for_week(args.chart, args.chart_date, db=db_path)
    else:
        year, month = map(int, args.year_month)
        df = get_top40_for_month(args.chart, year, month, db=db_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"[export_billboard_top40] wrote {len(df)} rows -> {out_path}")


if __name__ == "__main__":
    main()
