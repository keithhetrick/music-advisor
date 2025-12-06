#!/usr/bin/env python3
"""
Import Tier 2 lanes CSV into SQLite (spine_master_tier2_modern_lanes_v1 by default).
Paths are env-aware via ma_config (MA_SPINE_ROOT, MA_DATA_ROOT).
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import List

from ma_config.paths import get_spine_root, get_historical_echo_db_path


def create_table(conn: sqlite3.Connection, table: str, fieldnames: List[str], reset: bool = False) -> None:
    cur = conn.cursor()
    if reset:
        cur.execute(f'DROP TABLE IF EXISTS "{table}"')

    cols: List[str] = []
    seen = set()
    for name in fieldnames:
        name = (name or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        cols.append(name)

    col_defs = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
    for name in cols:
        col_defs.append(f'"{name}" TEXT')

    sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
    cur.execute(sql)
    conn.commit()


def import_csv(conn: sqlite3.Connection, table: str, csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        placeholders = ", ".join("?" for _ in fieldnames)
        cols = ", ".join(f'"{fn}"' for fn in fieldnames)
        sql = f'INSERT INTO "{table}" ({cols}) VALUES ({placeholders})'
        rows = [tuple(row.get(fn) for fn in fieldnames) for row in reader]
        conn.executemany(sql, rows)
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Tier 2 lanes CSV into SQLite (spine_master_tier2_modern_lanes_v1 by default)."
    )
    default_db = get_historical_echo_db_path()
    parser.add_argument("--db", default=str(default_db), help=f"SQLite DB path (default: {default_db}).")
    default_lanes = get_spine_root() / "spine_master_tier2_modern_lanes_v1.csv"
    parser.add_argument(
        "--spine-lanes",
        default=str(default_lanes),
        help="Tier 2 lanes CSV path.",
    )
    parser.add_argument(
        "--table",
        default="spine_master_tier2_modern_lanes_v1",
        help="Destination table name.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the destination table before import.",
    )

    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    csv_path = Path(args.spine_lanes).expanduser()

    print(f"[INFO] Loading Tier 2 lanes from {csv_path} ...")
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        print(f"[INFO] Detected {len(fieldnames)} CSV columns")

    print(f"[INFO] Connecting to DB: {db_path}")
    conn = sqlite3.connect(str(db_path))

    print(f"[INFO] Creating table {args.table} (reset={args.reset}) ...")
    create_table(conn, args.table, fieldnames, reset=args.reset)

    print(f"[INFO] Inserting rows into {args.table} ...")
    import_csv(conn, args.table, csv_path)

    conn.close()
    print(f"[INFO] Table {args.table} import complete.")


if __name__ == "__main__":
    main()
