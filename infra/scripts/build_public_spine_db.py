#!/usr/bin/env python3
"""
Build a SQLite spine DB from public CSVs.

Defaults:
- Data root: MA_DATA_ROOT or <repo>/data
- Input CSVs: <data_root>/public/spine/*.csv
- Output DB:  <data_root>/public/spine/spine_public.db

Usage:
  python infra/scripts/build_public_spine_db.py
  python infra/scripts/build_public_spine_db.py --out /path/to/spine_public.db --force
"""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = os.environ.get("MA_DATA_ROOT")
DEFAULT_DATA_ROOT = Path(DEFAULT_DATA_ROOT).expanduser() if DEFAULT_DATA_ROOT else REPO_ROOT / "data"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build SQLite spine DB from public CSVs.")
    ap.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Data root (default: MA_DATA_ROOT or ./data)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output SQLite DB path (default: <data_root>/public/spine/spine_public.db)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing DB if present",
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Rows per batch insert (default: 1000)",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any table is skipped (missing/invalid header)",
    )
    ap.add_argument(
        "--verify-counts",
        action="store_true",
        help="Compare CSV line counts to inserted rows and fail on mismatch",
    )
    ap.add_argument(
        "--safe-wal",
        action="store_true",
        help="Enable WAL + synchronous=FULL for crash safety (slower writes)",
    )
    ap.add_argument(
        "--paranoid",
        action="store_true",
        help="Enable extra checks (duplicate keys, numeric validation, integrity summary). Implies --strict.",
    )
    ap.add_argument(
        "--analyze",
        action="store_true",
        help="Run ANALYZE after import (adds time, improves query plans)",
    )
    ap.add_argument(
        "--log-path",
        type=Path,
        default=None,
        help="Optional log file (also prints to stdout). Default: logs/build_public_spine_db.log",
    )
    return ap.parse_args()


TABLE_SCHEMAS: Dict[str, str] = {
    "spine_master": """
        CREATE TABLE IF NOT EXISTS spine_master (
            spine_track_id TEXT PRIMARY KEY,
            year INTEGER,
            chart TEXT,
            year_end_rank INTEGER,
            echo_tier TEXT,
            artist TEXT,
            title TEXT,
            billboard_source TEXT,
            spotify_id TEXT,
            kaggle_track_id TEXT,
            kaggle_match_type TEXT,
            notes TEXT,
            acousticness REAL,
            audio_source TEXT,
            danceability REAL,
            duration_ms INTEGER,
            energy REAL,
            instrumentalness REAL,
            key INTEGER,
            liveness REAL,
            loudness REAL,
            mode INTEGER,
            speechiness REAL,
            tempo REAL,
            time_signature INTEGER,
            valence REAL
        );
        CREATE INDEX IF NOT EXISTS idx_spine_master_spotify_id ON spine_master(spotify_id);
    """,
    "spine_core_tracks_v1": """
        CREATE TABLE IF NOT EXISTS spine_core_tracks_v1 (
            spine_track_id TEXT PRIMARY KEY,
            year INTEGER,
            chart TEXT,
            year_end_rank INTEGER,
            echo_tier TEXT,
            artist TEXT,
            title TEXT,
            billboard_source TEXT,
            spotify_id TEXT,
            kaggle_track_id TEXT,
            kaggle_match_type TEXT,
            notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_core_spotify_id ON spine_core_tracks_v1(spotify_id);
    """,
    "spine_audio_spotify_v1": """
        CREATE TABLE IF NOT EXISTS spine_audio_spotify_v1 (
            spine_track_id TEXT PRIMARY KEY,
            kaggle_track_id TEXT,
            spotify_id TEXT,
            tempo REAL,
            loudness REAL,
            danceability REAL,
            energy REAL,
            valence REAL,
            acousticness REAL,
            instrumentalness REAL,
            liveness REAL,
            speechiness REAL,
            duration_ms INTEGER,
            key INTEGER,
            mode INTEGER,
            time_signature INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_audio_spotify_id ON spine_audio_spotify_v1(spotify_id);
    """,
    "spine_audio_spotify_v1_enriched": """
        CREATE TABLE IF NOT EXISTS spine_audio_spotify_v1_enriched (
            spine_track_id TEXT PRIMARY KEY,
            kaggle_track_id TEXT,
            spotify_id TEXT,
            acousticness REAL,
            artist TEXT,
            audio_source TEXT,
            danceability REAL,
            duration_ms INTEGER,
            energy REAL,
            instrumentalness REAL,
            key INTEGER,
            liveness REAL,
            loudness REAL,
            mode INTEGER,
            speechiness REAL,
            tempo REAL,
            time_signature INTEGER,
            title TEXT,
            valence REAL,
            year INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_audio_enriched_spotify_id ON spine_audio_spotify_v1_enriched(spotify_id);
    """,
    "spine_unmatched_billboard_v1": """
        CREATE TABLE IF NOT EXISTS spine_unmatched_billboard_v1 (
            year INTEGER,
            chart TEXT,
            year_end_rank INTEGER,
            echo_tier TEXT,
            artist TEXT,
            title TEXT,
            spotify_id TEXT,
            normalized_artist TEXT,
            normalized_title TEXT,
            matching_attempts INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_unmatched_artist_title ON spine_unmatched_billboard_v1(normalized_artist, normalized_title);
    """,
}

NUMERIC_FIELDS: Dict[str, Dict[str, str]] = {
    "spine_master": {
        "year": "int",
        "year_end_rank": "int",
        "duration_ms": "int",
        "key": "int",
        "mode": "int",
        "time_signature": "int",
        "acousticness": "float",
        "danceability": "float",
        "energy": "float",
        "instrumentalness": "float",
        "liveness": "float",
        "loudness": "float",
        "speechiness": "float",
        "tempo": "float",
        "valence": "float",
    },
    "spine_core_tracks_v1": {
        "year": "int",
        "year_end_rank": "int",
    },
    "spine_audio_spotify_v1": {
        "tempo": "float",
        "loudness": "float",
        "danceability": "float",
        "energy": "float",
        "valence": "float",
        "acousticness": "float",
        "instrumentalness": "float",
        "liveness": "float",
        "speechiness": "float",
        "duration_ms": "int",
        "key": "int",
        "mode": "int",
        "time_signature": "int",
    },
    "spine_audio_spotify_v1_enriched": {
        "acousticness": "float",
        "danceability": "float",
        "duration_ms": "int",
        "energy": "float",
        "instrumentalness": "float",
        "key": "int",
        "liveness": "float",
        "loudness": "float",
        "mode": "int",
        "speechiness": "float",
        "tempo": "float",
        "time_signature": "int",
        "valence": "float",
        "year": "int",
    },
    "spine_unmatched_billboard_v1": {
        "year": "int",
        "year_end_rank": "int",
        "matching_attempts": "int",
    },
}

TABLE_FILES: Dict[str, str] = {
    "spine_master": "spine_master.csv",
    "spine_core_tracks_v1": "spine_core_tracks_v1.csv",
    "spine_audio_spotify_v1": "spine_audio_spotify_v1.csv",
    "spine_audio_spotify_v1_enriched": "spine_audio_spotify_v1_enriched.csv",
    "spine_unmatched_billboard_v1": "spine_unmatched_billboard_v1.csv",
}

EXPECTED_HEADERS: Dict[str, Sequence[str]] = {
    "spine_master": [
        "spine_track_id",
        "year",
        "chart",
        "year_end_rank",
        "echo_tier",
        "artist",
        "title",
        "billboard_source",
        "spotify_id",
        "kaggle_track_id",
        "kaggle_match_type",
        "notes",
        "acousticness",
        "audio_source",
        "danceability",
        "duration_ms",
        "energy",
        "instrumentalness",
        "key",
        "liveness",
        "loudness",
        "mode",
        "speechiness",
        "tempo",
        "time_signature",
        "valence",
    ],
    "spine_core_tracks_v1": [
        "spine_track_id",
        "year",
        "chart",
        "year_end_rank",
        "echo_tier",
        "artist",
        "title",
        "billboard_source",
        "spotify_id",
        "kaggle_track_id",
        "kaggle_match_type",
        "notes",
    ],
    "spine_audio_spotify_v1": [
        "spine_track_id",
        "kaggle_track_id",
        "spotify_id",
        "tempo",
        "loudness",
        "danceability",
        "energy",
        "valence",
        "acousticness",
        "instrumentalness",
        "liveness",
        "speechiness",
        "duration_ms",
        "key",
        "mode",
        "time_signature",
    ],
    "spine_audio_spotify_v1_enriched": [
        "spine_track_id",
        "kaggle_track_id",
        "spotify_id",
        "acousticness",
        "artist",
        "audio_source",
        "danceability",
        "duration_ms",
        "energy",
        "instrumentalness",
        "key",
        "liveness",
        "loudness",
        "mode",
        "speechiness",
        "tempo",
        "time_signature",
        "title",
        "valence",
        "year",
    ],
    "spine_unmatched_billboard_v1": [
        "year",
        "chart",
        "year_end_rank",
        "echo_tier",
        "artist",
        "title",
        "spotify_id",
        "normalized_artist",
        "normalized_title",
        "matching_attempts",
    ],
}


def load_csv_rows_stream(path: Path, expected_fields: Sequence[str]) -> Iterable[Dict[str, str]]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh, fieldnames=list(expected_fields))
        next(reader, None)  # skip header row
        yield from reader


def create_tables(conn: sqlite3.Connection) -> None:
    for ddl in TABLE_SCHEMAS.values():
        conn.executescript(ddl)


def insert_rows_stream(
    conn: sqlite3.Connection,
    table: str,
    rows: Iterable[Dict[str, str]],
    batch_size: int,
    paranoid: bool,
) -> Tuple[int, List[str]]:
    total = 0
    cols: List[str] = []
    sql = ""
    batch: List[Dict[str, str]] = []
    errors: List[str] = []
    seen_keys = set() if paranoid and table != "spine_unmatched_billboard_v1" else None
    numeric_map = NUMERIC_FIELDS.get(table, {})
    for row in rows:
        if not cols:
            cols = list(row.keys())
            placeholders = ",".join([":" + c for c in cols])
            sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders});"
        # Paranoid: numeric coercion
        if numeric_map:
            for field, typ in numeric_map.items():
                if field not in row:
                    continue
                val = row[field].strip() if isinstance(row[field], str) else row[field]
                if val == "":
                    row[field] = None
                    continue
                try:
                    if typ == "int":
                        row[field] = int(float(val))
                    else:
                        row[field] = float(val)
                except Exception:
                    errors.append(f"[build-spine-db] numeric parse failed ({table}.{field}): {val!r}")
                    row[field] = None
        # Paranoid: duplicate key check (by spine_track_id where applicable)
        if seen_keys is not None and "spine_track_id" in row:
            key = row["spine_track_id"]
            if key in seen_keys:
                errors.append(f"[build-spine-db] duplicate spine_track_id in {table}: {key}")
            else:
                seen_keys.add(key)
        batch.append(row)
        if len(batch) >= batch_size:
            conn.executemany(sql, batch)
            total += len(batch)
            batch = []
    if batch:
        conn.executemany(sql, batch)
        total += len(batch)
    return total, errors


def main() -> int:
    args = parse_args()
    if args.paranoid:
        args.strict = True

    log_path = args.log_path or Path("logs") / "build_public_spine_db.log"
    log_path = log_path.expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        print(msg)
        try:
            with log_path.open("a", encoding="utf-8") as lf:
                lf.write(msg + "\n")
        except Exception:
            pass

    data_root: Path = args.data_root.expanduser()
    public_root = data_root / "public" / "spine"
    out_db = args.out.expanduser() if args.out else public_root / "spine_public.db"

    if out_db.exists() and not args.force:
        log(f"[build-spine-db] {out_db} exists; use --force to overwrite")
        return 1
    if out_db.exists() and args.force:
        out_db.unlink()

    out_db.parent.mkdir(parents=True, exist_ok=True)

    required_missing: List[str] = []
    issues: List[str] = []  # hard failures
    warnings: List[str] = []  # non-fatal notices
    table_counts: Dict[str, int] = {}
    csv_counts: Dict[str, int] = {}

    conn = sqlite3.connect(str(out_db))
    if args.safe_wal:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=FULL;")
    try:
        create_tables(conn)
        for table, filename in TABLE_FILES.items():
            csv_path = public_root / filename
            if not csv_path.exists():
                required_missing.append(str(csv_path))
                continue
            with csv_path.open(newline="") as fh:
                reader = csv.reader(fh)
                try:
                    header = [h.strip() for h in next(reader)]
                except StopIteration:
                    issues.append(f"[build-spine-db] empty CSV: {csv_path}")
                    continue
            expected = EXPECTED_HEADERS.get(table, [])
            if list(header) != list(expected):
                issues.append(
                    f"[build-spine-db] header mismatch for {table}: expected {expected}, got {header}"
                )
                continue

            with conn:
                rows_stream = load_csv_rows_stream(csv_path, expected)
                inserted, errs = insert_rows_stream(conn, table, rows_stream, args.batch_size, args.paranoid)
                table_counts[table] = inserted
                warnings.extend(errs)
                if args.verify_counts:
                    # count lines minus header
                    with csv_path.open() as fh:
                        total_lines = sum(1 for _ in fh)
                    csv_counts[table] = max(total_lines - 1, 0)
            log(f"[build-spine-db] imported {inserted:,} rows into {table}")
        if args.analyze:
            conn.execute("ANALYZE;")
    finally:
        conn.close()

    if required_missing:
        for msg in required_missing:
            log(f"[build-spine-db] missing required CSV: {msg}")
    if issues:
        for msg in issues:
            log(msg)
    if args.strict and (required_missing or issues):
        return 1
    if warnings:
        for msg in warnings:
            log(msg)
    if args.verify_counts:
        mismatches = []
        for table, inserted in table_counts.items():
            expected_rows = csv_counts.get(table, inserted)
            if inserted != expected_rows:
                mismatches.append(f"[build-spine-db] rowcount mismatch for {table}: inserted {inserted}, csv rows {expected_rows}")
        if mismatches:
            for m in mismatches:
                log(m)
            return 1

    for table, count in sorted(table_counts.items()):
        log(f"[build-spine-db] rowcount {table}: {count:,}")

    log(f"[build-spine-db] done -> {out_db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
