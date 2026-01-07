#!/usr/bin/env python3
"""
historical_echo_db_import.py

Import one or more Historical Echo corpus CSVs into a SQLite database.

This is the first step toward a proper "credit bureau" for songs:
- tracks        : identity + cohort membership (calibration / echo)
- audio_features: axes extracted by the audio engine
- hci_scores    : raw / calibrated / final HCI + HCI_audio_v2.raw

Typical usage:

    cd MusicAdvisor

    python tools/historical_echo_db_import.py \
        --csv data/historical_echo_corpus_2025Q4.csv \
        --db data/historical_echo/historical_echo.db \
        --reset

You can run this repeatedly as the corpus grows; rows are keyed by
track slug and will be upserted (INSERT OR REPLACE on feature/score tables).
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional
from shared.security import db as sec_db


# -------------------------------------------------------------------
# Small helpers
# -------------------------------------------------------------------


def _bool_from_csv(value: Any) -> int:
    """
    Convert CSV 'True'/'False'/1/0/'' into an integer 0/1 for SQLite.
    """
    if value is None:
        return 0
    s = str(value).strip().lower()
    if s in ("1", "true", "yes", "y"):
        return 1
    return 0


def _float_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


# -------------------------------------------------------------------
# DB schema
# -------------------------------------------------------------------


CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        year TEXT,
        artist TEXT,
        title TEXT,
        region TEXT,
        profile TEXT,
        source_root TEXT,
        set_name TEXT,
        market_baseline_id TEXT,
        hci_role TEXT,
        in_calibration_set INTEGER,
        in_echo_set INTEGER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS audio_features (
        track_id INTEGER PRIMARY KEY,
        tempo_fit REAL,
        runtime_fit REAL,
        loudness_fit REAL,
        energy REAL,
        danceability REAL,
        valence REAL,
        FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS hci_scores (
        track_id INTEGER PRIMARY KEY,
        hci_v1_score_raw REAL,
        hci_v1_score REAL,
        hci_v1_final_score REAL,
        hci_audio_v2_raw REAL,
        FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
    );
    """,
    # Helpful indexes
    """
    CREATE INDEX IF NOT EXISTS idx_tracks_slug ON tracks(slug);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_tracks_set_name ON tracks(set_name);
    """,
]


def init_db(db_path: Path, reset: bool) -> sqlite3.Connection:
    """
    Open the SQLite DB and ensure base tables exist.

    If reset=True and the target path already exists but is not a valid
    SQLite DB (or you just want a clean slate), we remove the file first
    and then create a fresh DB.
    """
    # Ensure directory exists
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # If reset requested and file already exists, just delete it so we
    # don't run into "file is not a database" errors on corrupt/old files.
    if reset and db_path.exists():
        print(f"[INFO] Reset requested; removing existing DB file: {db_path}")
        db_path.unlink()

    # Now open a (possibly new) DB file
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # If reset is requested *after* we just removed the file, tables won't
    # exist yet, but DROP TABLE IF EXISTS is safe either way. This also
    # covers the case where you run without --reset initially, then later
    # add --reset and want a clean schema.
    if reset:
        print(f"[INFO] Resetting schema in {db_path}")
        for table in ("hci_scores", "audio_features", "tracks"):
            sec_db.validate_table_name(table)
            sec_db.safe_execute(conn, f"DROP TABLE IF EXISTS {table};")

    for stmt in CREATE_TABLES_SQL:
        cur.execute(stmt)

    conn.commit()
    return conn


# -------------------------------------------------------------------
# Import logic
# -------------------------------------------------------------------


def upsert_track(
    conn: sqlite3.Connection,
    row: Dict[str, Any],
) -> int:
    """
    Insert or update a track row and return track_id.
    """
    slug = row.get("slug")
    if not slug:
        raise ValueError("Row missing 'slug' column; cannot import.")

    slug = str(slug)

    cur = conn.cursor()
    cur.execute("SELECT id FROM tracks WHERE slug = ?", (slug,))
    res = cur.fetchone()
    if res is not None:
        track_id = int(res[0])
        # Update existing record with latest metadata
        cur.execute(
            """
            UPDATE tracks
            SET year = ?, artist = ?, title = ?, region = ?, profile = ?,
                source_root = ?, set_name = ?, market_baseline_id = ?,
                hci_role = ?, in_calibration_set = ?, in_echo_set = ?
            WHERE id = ?
            """,
            (
                row.get("year"),
                row.get("artist"),
                row.get("title"),
                row.get("region"),
                row.get("profile"),
                row.get("source_root"),
                row.get("set_name"),
                row.get("market_baseline_id"),
                row.get("hci_role"),
                _bool_from_csv(row.get("in_calibration_set")),
                _bool_from_csv(row.get("in_echo_set")),
                track_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO tracks (
                slug, year, artist, title, region, profile,
                source_root, set_name, market_baseline_id,
                hci_role, in_calibration_set, in_echo_set
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slug,
                row.get("year"),
                row.get("artist"),
                row.get("title"),
                row.get("region"),
                row.get("profile"),
                row.get("source_root"),
                row.get("set_name"),
                row.get("market_baseline_id"),
                row.get("hci_role"),
                _bool_from_csv(row.get("in_calibration_set")),
                _bool_from_csv(row.get("in_echo_set")),
            ),
        )
        track_id = cur.lastrowid

    return track_id


def upsert_audio_features(
    conn: sqlite3.Connection,
    track_id: int,
    row: Dict[str, Any],
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO audio_features (
            track_id, tempo_fit, runtime_fit, loudness_fit,
            energy, danceability, valence
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(track_id) DO UPDATE SET
            tempo_fit = excluded.tempo_fit,
            runtime_fit = excluded.runtime_fit,
            loudness_fit = excluded.loudness_fit,
            energy = excluded.energy,
            danceability = excluded.danceability,
            valence = excluded.valence;
        """,
        (
            track_id,
            _float_or_none(row.get("tempo_fit")),
            _float_or_none(row.get("runtime_fit")),
            _float_or_none(row.get("loudness_fit")),
            _float_or_none(row.get("energy")),
            _float_or_none(row.get("danceability")),
            _float_or_none(row.get("valence")),
        ),
    )


def upsert_hci_scores(
    conn: sqlite3.Connection,
    track_id: int,
    row: Dict[str, Any],
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO hci_scores (
            track_id, hci_v1_score_raw, hci_v1_score,
            hci_v1_final_score, hci_audio_v2_raw
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(track_id) DO UPDATE SET
            hci_v1_score_raw = excluded.hci_v1_score_raw,
            hci_v1_score = excluded.hci_v1_score,
            hci_v1_final_score = excluded.hci_v1_final_score,
            hci_audio_v2_raw = excluded.hci_audio_v2_raw;
        """,
        (
            track_id,
            _float_or_none(row.get("hci_v1_score_raw")),
            _float_or_none(row.get("hci_v1_score")),
            _float_or_none(row.get("hci_v1_final_score")),
            _float_or_none(row.get("hci_audio_v2_raw")),
        ),
    )


def import_csv(
    conn: sqlite3.Connection,
    csv_path: Path,
    verbose: bool = False,
) -> int:
    """
    Import a single CSV file into the DB.
    Returns number of rows imported.
    """
    print(f"[INFO] Importing {csv_path}")
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            slug = row.get("slug")
            if not slug:
                if verbose:
                    print("[WARN] Skipping row without slug")
                continue

            track_id = upsert_track(conn, row)
            upsert_audio_features(conn, track_id, row)
            upsert_hci_scores(conn, track_id, row)
            count += 1

            if verbose and count % 100 == 0:
                print(f"[INFO]  imported {count} rows so far...")

    conn.commit()
    print(f"[OK] Imported {count} rows from {csv_path}")
    return count


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Import Historical Echo corpus CSV into a SQLite DB."
    )
    ap.add_argument(
        "--csv",
        action="append",
        required=True,
        help="Path to corpus CSV (can be passed multiple times).",
    )
    ap.add_argument(
        "--db",
        required=True,
        help="Path to SQLite database file to create/update, e.g. data/historical_echo/historical_echo.db",
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing tables (tracks/audio_features/hci_scores) and recreate them. "
             "If the DB file already exists, it will be deleted first.",
    )
    ap.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose progress logging.",
    )

    args = ap.parse_args()

    db_path = Path(args.db)
    conn = init_db(db_path, reset=args.reset)

    total = 0
    for csv_str in args.csv:
        csv_path = Path(csv_str)
        if not csv_path.exists():
            print(f"[WARN] CSV not found: {csv_path}")
            continue
        total += import_csv(conn, csv_path, verbose=args.verbose)

    print(f"[DONE] Total imported rows: {total}")
    conn.close()


if __name__ == "__main__":
    main()
