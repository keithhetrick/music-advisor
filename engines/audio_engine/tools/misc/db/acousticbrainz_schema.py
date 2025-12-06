"""
acousticbrainz_schema.py

DDL helpers for staging MusicBrainz MBID mappings and a compact subset of
AcousticBrainz features. These are Tier 3 only tables that live alongside
historical_echo data but do not modify Tier 1 / Tier 2 schemas.
"""
from __future__ import annotations

import sqlite3
from typing import Optional


def ensure_acousticbrainz_tables(conn: sqlite3.Connection, reset: bool = False) -> None:
    """
    Create MusicBrainz and AcousticBrainz staging tables if they do not exist.
    Safe to call repeatedly. Optional reset will drop/recreate the tables.
    """
    cur = conn.cursor()
    if reset:
        cur.execute("DROP TABLE IF EXISTS spine_musicbrainz_map_v1")
        cur.execute("DROP TABLE IF EXISTS features_external_acousticbrainz_v1")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS spine_musicbrainz_map_v1 (
            id INTEGER PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            title TEXT,
            artist TEXT,
            year INTEGER,
            recording_mbid TEXT,
            mbid_confidence REAL,
            source TEXT DEFAULT 'musicbrainz_api',
            created_at TEXT,
            updated_at TEXT
        );
        """
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_spine_musicbrainz_map_slug ON spine_musicbrainz_map_v1 (slug);"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_spine_musicbrainz_map_mbid ON spine_musicbrainz_map_v1 (recording_mbid);"
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS features_external_acousticbrainz_v1 (
            id INTEGER PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            recording_mbid TEXT NOT NULL,
            feature_source TEXT DEFAULT 'acousticbrainz',
            features_json TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_features_ext_acb_slug ON features_external_acousticbrainz_v1 (slug);"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_features_ext_acb_mbid ON features_external_acousticbrainz_v1 (recording_mbid);"
    )

    conn.commit()


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def ensure_tables_if_db_present(db_path: str | None) -> Optional[sqlite3.Connection]:
    """
    Convenience helper: open DB if path is provided and ensure tables exist.
    Returns an open connection or None if db_path is falsy.
    """
    if not db_path:
        return None
    conn = sqlite3.connect(db_path)
    ensure_acousticbrainz_tables(conn)
    return conn
