#!/usr/bin/env python3
"""
build_spine_success_from_ut_hot100_v1.py

Derive per-track Hot 100 success metrics from UT weekly data and attach
them to the spine via `spine_track_id`.

Inputs:
  - SQLite DB with `spine_master_v1_lanes` (or `spine_v1` as fallback).
  - UT weekly Hot 100 CSV (e.g. data/ut_hot_100_1958_present.csv).

Output:
  - Table `spine_success_ut_hot100_v1` inside the same DB.

Metrics per spine_track_id:
  - weeks_on_hot100
  - peak_hot100_pos
  - first_hot100_date
  - last_hot100_date
  - hot100_entries_count
  - ut_slug (for debugging)

Usage:

    source .venv/bin/activate

    python tools/spine/build_spine_success_from_ut_hot100_v1.py \
      --db data/private/local_assets/historical_echo/historical_echo.db \
      --ut-hot100 data/private/local_assets/external/weekly/ut_hot_100_1958_present.csv \
      --reset
"""

import argparse
import csv
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import re

from shared.security import db as sec_db
from shared.config.paths import get_external_data_root, get_historical_echo_db_path


def norm_text(s: str) -> str:
    if s is None:
        return ""
    s = s.lower()
    # Basic cleanup: remove ft/feat, punctuation-ish characters, collapse spaces
    s = re.sub(r"\b(feat\.?|ft\.?)\b", "", s)
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def make_slug(title: str, artist: str) -> str:
    return norm_text(title) + "___" + norm_text(artist)


def load_ut_hot100(path):
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"[ERROR] UT Hot 100 file not found: {path}")

    print(f"[INFO] Loading UT Hot 100 weekly from {path} ...")
    # Expected columns (from ut_hot_100_1958_present.csv):
    # chart_week, current_week, title, performer, last_week, peak_pos, wks_on_chart
    metrics = {}

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        agg = defaultdict(
            lambda: {
                "weeks_on_hot100": 0,
                "peak_hot100_pos": None,
                "first_hot100_date": None,
                "last_hot100_date": None,
                "hot100_entries_count": 0,
            }
        )
        for row in reader:
            title = row.get("title", "")
            artist = row.get("performer", "")
            slug = make_slug(title, artist)
            if not slug:
                continue

            chart_week = row.get("chart_week")
            peak_pos = row.get("peak_pos")
            wks_on_chart = row.get("wks_on_chart")

            try:
                dt = datetime.strptime(chart_week, "%Y-%m-%d").date()
            except Exception:
                dt = None

            try:
                peak_pos = int(peak_pos)
            except Exception:
                peak_pos = None

            try:
                wks_on_chart = int(wks_on_chart)
            except Exception:
                wks_on_chart = None

            rec = agg[slug]
            rec["hot100_entries_count"] += 1
            if wks_on_chart is not None and wks_on_chart > (rec["weeks_on_hot100"] or 0):
                rec["weeks_on_hot100"] = wks_on_chart
            if peak_pos is not None:
                if rec["peak_hot100_pos"] is None or peak_pos < rec["peak_hot100_pos"]:
                    rec["peak_hot100_pos"] = peak_pos
            if dt is not None:
                if rec["first_hot100_date"] is None or dt < rec["first_hot100_date"]:
                    rec["first_hot100_date"] = dt
                if rec["last_hot100_date"] is None or dt > rec["last_hot100_date"]:
                    rec["last_hot100_date"] = dt

    # Convert dates back to ISO strings
    for slug, rec in agg.items():
        if rec["first_hot100_date"] is not None:
            rec["first_hot100_date"] = rec["first_hot100_date"].isoformat()
        if rec["last_hot100_date"] is not None:
            rec["last_hot100_date"] = rec["last_hot100_date"].isoformat()

    print(f"[INFO] Aggregated UT metrics for {len(agg)} unique slugs")
    return agg


def load_spine(conn):
    cur = conn.cursor()
    # Prefer spine_master_v1_lanes; fall back to spine_v1
    table = None
    for candidate in ("spine_master_v1_lanes", "spine_v1"):
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (candidate,)
        )
        if cur.fetchone():
            table = sec_db.validate_table_name(candidate)
            break
    if not table:
        raise SystemExit(
            "[ERROR] Neither spine_master_v1_lanes nor spine_v1 found in DB."
        )

    print(f"[INFO] Reading spine from table: {table}")
    cur = sec_db.safe_execute(conn, f"SELECT spine_track_id, year, artist, title FROM {table}")
    rows = cur.fetchall()
    return table, rows


def create_success_table(conn, reset=False):
    cur = conn.cursor()
    if reset:
        sec_db.safe_execute(conn, "DROP TABLE IF EXISTS spine_success_ut_hot100_v1")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS spine_success_ut_hot100_v1 (
            spine_track_id      TEXT PRIMARY KEY,
            weeks_on_hot100     INTEGER,
            peak_hot100_pos     INTEGER,
            first_hot100_date   TEXT,
            last_hot100_date    TEXT,
            hot100_entries_count INTEGER,
            ut_slug             TEXT
        );
        """
    )
    conn.commit()


def main():
    ap = argparse.ArgumentParser(
        description="Build spine_success_ut_hot100_v1 from UT weekly Hot 100."
    )
    ap.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help="Path to SQLite DB (default honors MA_DATA_ROOT).",
    )
    ap.add_argument(
        "--ut-hot100",
        default=str(get_external_data_root() / "weekly/ut_hot_100_1958_present.csv"),
        help="Path to UT Hot 100 weekly CSV (default under private/local_assets/external/weekly).",
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate spine_success_ut_hot100_v1 before inserting.",
    )
    args = ap.parse_args()

    ut_metrics = load_ut_hot100(args.ut_hot100)

    db_path = Path(args.db)
    print(f"[INFO] Connecting to DB: {db_path}")
    conn = sqlite3.connect(db_path)

    table, spine_rows = load_spine(conn)

    print(f"[INFO] Loaded {len(spine_rows)} rows from {table}")
    create_success_table(conn, reset=args.reset)

    cur = conn.cursor()
    matched = 0
    unmatched = 0

    print("[INFO] Inserting per-track success metrics ...")
    for spine_track_id, year, artist, title in spine_rows:
        slug = make_slug(title or "", artist or "")
        rec = ut_metrics.get(slug)
        if rec is None:
            unmatched += 1
            cur.execute(
                """
                INSERT OR REPLACE INTO spine_success_ut_hot100_v1
                    (spine_track_id, weeks_on_hot100, peak_hot100_pos,
                     first_hot100_date, last_hot100_date, hot100_entries_count, ut_slug)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (spine_track_id, None, None, None, None, None, slug),
            )
        else:
            matched += 1
            cur.execute(
                """
                INSERT OR REPLACE INTO spine_success_ut_hot100_v1
                    (spine_track_id, weeks_on_hot100, peak_hot100_pos,
                     first_hot100_date, last_hot100_date, hot100_entries_count, ut_slug)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    spine_track_id,
                    rec["weeks_on_hot100"],
                    rec["peak_hot100_pos"],
                    rec["first_hot100_date"],
                    rec["last_hot100_date"],
                    rec["hot100_entries_count"],
                    slug,
                ),
            )

    conn.commit()
    print("[INFO] Success table populated.")
    print(f"[INFO] Matched  : {matched}")
    print(f"[INFO] Unmatched: {unmatched}")

    conn.close()
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
