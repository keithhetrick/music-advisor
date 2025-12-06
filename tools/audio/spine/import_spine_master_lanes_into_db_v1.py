#!/usr/bin/env python
"""
import_spine_master_lanes_into_db_v1.py

Import data/spine/spine_master_v1_lanes.csv into SQLite as a table
(spine_master_v1_lanes by default).

Usage:

  python tools/spine/import_spine_master_lanes_into_db_v1.py \
    --db data/private/local_assets/historical_echo/historical_echo.db \
    --spine-lanes data/public/spine/spine_master_v1_lanes.csv \
    --reset

Notes:
- All columns from the CSV are created as TEXT columns (simple + robust).
- Duplicate column names in the CSV are deduplicated, keeping the first.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import List

from ma_config.paths import get_historical_echo_db_path, get_spine_root

def create_table(conn: sqlite3.Connection, table: str, fieldnames: List[str], reset: bool = False) -> None:
    cur = conn.cursor()

    if reset:
        cur.execute(f'DROP TABLE IF EXISTS "{table}"')

    # Deduplicate columns while preserving order
    cols: List[str] = []
    seen = set()
    for name in fieldnames:
        name = (name or "").strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        cols.append(name)

    col_defs = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
    for name in cols:
        col_defs.append(f'"{name}" TEXT')

    sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
    cur.execute(sql)
    conn.commit()

    return


def import_csv(conn: sqlite3.Connection, table: str, csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn for fn in (reader.fieldnames or []) if fn]

        # Rebuild column list in the same deduped order used in create_table
        cols: List[str] = []
        seen = set()
        for name in fieldnames:
            name = (name or "").strip()
            if not name:
                continue
            if name in seen:
                continue
            seen.add(name)
            cols.append(name)

        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(f'"{c}"' for c in cols)
        sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

        cur = conn.cursor()
        count = 0
        for row in reader:
            values = [row.get(c) for c in cols]
            cur.execute(sql, values)
            count += 1

        conn.commit()
        print(f"[INFO] Inserted {count} rows into {table}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import spine_master_v1_lanes CSV into historical_echo.db."
    )
    parser.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help="Path to SQLite DB (default honors MA_DATA_ROOT/historical_echo/historical_echo.db)",
    )
    parser.add_argument(
        "--spine-lanes",
        default=str(get_spine_root() / "spine_master_v1_lanes.csv"),
        help="Path to spine_master_v1_lanes CSV.",
    )
    parser.add_argument(
        "--table",
        default="spine_master_v1_lanes",
        help="Destination table name (default: spine_master_v1_lanes).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the destination table before import.",
    )

    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    csv_path = Path(args.spine_lanes).expanduser()

    print(f"[INFO] Loading spine lanes from {csv_path} ...")
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
