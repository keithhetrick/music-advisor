#!/usr/bin/env python3
"""
Report coverage for market_norms Billboard SQLite DB.

Usage:
  python tools/market_norms_db_report.py --db <DATA_ROOT>/market_norms/market_norms_billboard.db
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from ma_config.paths import get_data_root


def fetch(conn, table: str):
    cur = conn.cursor()
    cur.execute(f"SELECT MIN(chart_date), MAX(chart_date), COUNT(*) FROM {table}")
    return cur.fetchone()


def main() -> None:
    ap = argparse.ArgumentParser(description="Show chart coverage for the Billboard DB.")
    default_db = get_data_root() / "market_norms" / "market_norms_billboard.db"
    ap.add_argument(
        "--db",
        default=str(default_db),
        help=f"Path to market_norms_billboard.db (default: {default_db})",
    )
    args = ap.parse_args()

    db_path = Path(args.db)
    conn = sqlite3.connect(str(db_path))
    for table in ("hot100_weekly", "bb200_weekly"):
        row = fetch(conn, table)
        print(f"{table}: min_date={row[0]}, max_date={row[1]}, rows={row[2]}")
    conn.close()


if __name__ == "__main__":
    main()
