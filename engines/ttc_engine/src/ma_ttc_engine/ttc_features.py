"""
TTC feature computation placeholder.
"""
from __future__ import annotations

import sqlite3
from typing import Dict


def build_ttc_features_stub() -> Dict[str, float]:
    return {"ttc_seconds_first_chorus": 0.0, "ttc_bar_position_first_chorus": 0.0}


def write_ttc_features(
    conn: sqlite3.Connection,
    song_id: str,
    features: Dict[str, float],
    profile: str,
    estimation_method: str,
    ttc_confidence: str,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO features_ttc
            (song_id, ttc_seconds_first_chorus, ttc_bar_position_first_chorus, estimation_method, profile, ttc_confidence)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            song_id,
            features.get("ttc_seconds_first_chorus"),
            features.get("ttc_bar_position_first_chorus"),
            estimation_method,
            profile,
            ttc_confidence,
        ),
    )
    conn.commit()
