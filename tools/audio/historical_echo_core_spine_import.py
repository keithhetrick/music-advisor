#!/usr/bin/env python3
"""
historical_echo_core_spine_import.py

Purpose
-------
Import the "core hit spine" (~1,600 songs: Top N per year) into
historical_echo.db as a separate table called `core_spine`.

This table is *metadata-only*:
  - It does NOT touch your existing `tracks` table or HCI_v1 data.
  - It exists so that future HCI_v2 / Historical Echo layers can
    anchor themselves on a clean, auditable list of Top-40-per-year
    songs over ~40 years.

Expected input CSV (e.g. data/core_1600_with_spotify.csv) has at least:

  year,title,artist,year_end_rank,best_rank,weeks_on_chart,chart_points

and optionally:

  spotify_id,spotify_name,spotify_artist,spotify_album,
  release_date,track_popularity

These are exactly the columns produced by:

  - build_core_1600_from_hot100_current.py
  - spotify_enrich_core_corpus.py

Schema
------
Table: core_spine

  id                   INTEGER PRIMARY KEY AUTOINCREMENT
  year                 INTEGER
  title                TEXT
  artist               TEXT
  year_end_rank        INTEGER    -- 1..N per year
  best_rank            INTEGER    -- best weekly Hot 100 position
  weeks_on_chart       INTEGER
  chart_points         REAL       -- summed points(weekly rank)
  spotify_id           TEXT
  spotify_name         TEXT
  spotify_artist       TEXT
  spotify_album        TEXT
  spotify_release_date TEXT
  spotify_popularity   REAL       -- track_popularity from Spotify

Usage
-----

  cd ~/music-advisor

  # Create/overwrite the core_spine table from the enriched 1,600-song corpus
  python tools/historical_echo_core_spine_import.py \
    --csv data/core_1600_with_spotify.csv \
    --db  data/historical_echo/historical_echo.db \
    --reset-core

After running that, `historical_echo.db` will contain a `core_spine`
table we can use as the historical backbone for HCI_v2.
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

from shared.config.paths import get_core_spine_root, get_historical_echo_db_path


def ensure_core_spine_schema(conn: sqlite3.Connection, reset_core: bool = False) -> None:
    """
    Ensure that the `core_spine` table exists with the expected schema.

    If reset_core=True, we DROP TABLE core_spine first.
    """
    cur = conn.cursor()

    if reset_core:
        print("[INFO] --reset-core requested; dropping existing core_spine table if it exists.")
        cur.execute("DROP TABLE IF EXISTS core_spine;")
        conn.commit()

    # Create table if needed
    print("[INFO] Ensuring core_spine schema exists...")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS core_spine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            title TEXT,
            artist TEXT,
            year_end_rank INTEGER,
            best_rank INTEGER,
            weeks_on_chart INTEGER,
            chart_points REAL,
            spotify_id TEXT,
            spotify_name TEXT,
            spotify_artist TEXT,
            spotify_album TEXT,
            spotify_release_date TEXT,
            spotify_popularity REAL
        );
        """
    )
    conn.commit()


def _safe_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.upper() == "NA":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.upper() == "NA":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def import_core_spine(csv_path: Path, db_path: Path, reset_core: bool = False) -> None:
    """
    Main import routine: read the enriched 1,600-song CSV and populate
    the core_spine table.
    """
    if not csv_path.exists():
        raise SystemExit(f"[ERROR] Input CSV not found: {csv_path}")

    print(f"[INFO] Importing core spine from {csv_path} into {db_path}")

    # Ensure DB directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        ensure_core_spine_schema(conn, reset_core=reset_core)

        with csv_path.open("r", newline="", encoding="utf-8") as f_in:
            reader = csv.DictReader(f_in)
            rows = list(reader)

        if not rows:
            raise SystemExit(f"[ERROR] Input CSV {csv_path} is empty.")

        print(f"[INFO] Input CSV has {len(rows)} rows; inserting into core_spine...")

        cur = conn.cursor()
        inserted = 0

        for idx, row in enumerate(rows, start=1):
            year = _safe_int(row.get("year") or row.get("Year"))
            title = (row.get("title") or row.get("Title") or "").strip()
            artist = (row.get("artist") or row.get("Artist") or "").strip()

            if year is None or not title or not artist:
                print(f"[WARN] Skipping row {idx}: missing year/title/artist")
                continue

            year_end_rank = _safe_int(
                row.get("year_end_rank")
                or row.get("year_end_position")
                or row.get("Year_End_Rank")
            )
            best_rank = _safe_int(row.get("best_rank") or row.get("Best_Rank"))
            weeks_on_chart = _safe_int(
                row.get("weeks_on_chart")
                or row.get("Weeks_On_Chart")
                or row.get("wks_on_chart")
            )
            chart_points = _safe_float(
                row.get("chart_points") or row.get("Chart_Points")
            )

            spotify_id = (row.get("spotify_id") or "").strip()
            spotify_name = (row.get("spotify_name") or "").strip()
            spotify_artist = (row.get("spotify_artist") or "").strip()
            spotify_album = (row.get("spotify_album") or "").strip()
            spotify_release_date = (row.get("release_date") or "").strip()
            spotify_popularity = _safe_float(
                row.get("track_popularity") or row.get("spotify_popularity")
            )

            cur.execute(
                """
                INSERT INTO core_spine (
                    year,
                    title,
                    artist,
                    year_end_rank,
                    best_rank,
                    weeks_on_chart,
                    chart_points,
                    spotify_id,
                    spotify_name,
                    spotify_artist,
                    spotify_album,
                    spotify_release_date,
                    spotify_popularity
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    year,
                    title,
                    artist,
                    year_end_rank,
                    best_rank,
                    weeks_on_chart,
                    chart_points,
                    spotify_id,
                    spotify_name,
                    spotify_artist,
                    spotify_album,
                    spotify_release_date,
                    spotify_popularity,
                ),
            )
            inserted += 1

            if inserted % 200 == 0:
                print(f"[INFO] Inserted {inserted} rows so far...")

        conn.commit()
        print(f"[DONE] Imported {inserted} rows into core_spine.")

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import the core 1,600-song Billboard+Spotify spine into historical_echo.db."
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=str(get_core_spine_root() / "core_1600_with_spotify.csv"),
        help="Input CSV path (default: core_1600_with_spotify.csv under private/local_assets/core_spine).",
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        default=str(get_historical_echo_db_path()),
        help="SQLite DB path (default honors MA_DATA_ROOT).",
    )
    parser.add_argument(
        "--reset-core",
        action="store_true",
        help="Drop and recreate the core_spine table before import.",
    )

    args = parser.parse_args()

    import_core_spine(
        csv_path=Path(args.csv_path),
        db_path=Path(args.db_path),
        reset_core=args.reset_core,
    )


if __name__ == "__main__":
    main()
