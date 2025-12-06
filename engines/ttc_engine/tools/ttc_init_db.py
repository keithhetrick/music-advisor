#!/usr/bin/env python3
"""
Initialize TTC sidecar tables in a SQLite database.

Tables (all CREATE IF NOT EXISTS):
- ttc_corpus_stats: ground-truth TTC per dataset song id.
- ttc_local_estimates: optional local/audio-based TTC estimates.
- ttc_spine_map: optional mapping from dataset ids to spine slugs.

This script is idempotent and does not alter existing tables.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable

from ma_config.paths import get_historical_echo_db_path

DEFAULT_DB = get_historical_echo_db_path()


CREATE_STATEMENTS: Iterable[str] = (
    """
    CREATE TABLE IF NOT EXISTS ttc_corpus_stats (
        id INTEGER PRIMARY KEY,
        dataset_name TEXT NOT NULL,
        dataset_song_id TEXT NOT NULL,
        title TEXT,
        artist TEXT,
        year INTEGER,
        slug TEXT,
        ttc_seconds REAL,
        ttc_beats REAL,
        ttc_bars REAL,
        chorus_label_used TEXT,
        created_at_utc TEXT DEFAULT (datetime('now')),
        UNIQUE(dataset_name, dataset_song_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ttc_local_estimates (
        slug TEXT PRIMARY KEY,
        ttc_seconds REAL,
        ttc_beats REAL,
        ttc_bars REAL,
        method TEXT,
        confidence REAL,
        created_at_utc TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ttc_spine_map (
        dataset_name TEXT NOT NULL,
        dataset_song_id TEXT NOT NULL,
        slug TEXT NOT NULL,
        match_confidence REAL,
        PRIMARY KEY (dataset_name, dataset_song_id)
    );
    """,
)


def ensure_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def init_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    for stmt in CREATE_STATEMENTS:
        cur.execute(stmt)
    conn.commit()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Create TTC sidecar tables in a SQLite DB (idempotent).")
    ap.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help=f"Path to SQLite DB (default: {DEFAULT_DB}).",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).expanduser()
    conn = ensure_db(db_path)
    init_tables(conn)
    conn.close()
    print(f"[ttc_init_db] ensured TTC tables in {db_path}")


if __name__ == "__main__":
    main()
