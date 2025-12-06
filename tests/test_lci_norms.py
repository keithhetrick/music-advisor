import sqlite3
import json
from pathlib import Path

from ma_lyrics_engine.schema import ensure_schema
from ma_lyrics_engine.lci_norms import build_lane_norms


def seed_lci_row(conn, song_id, tier, era, axes, score, ttc_seconds, profile="lci_us_pop_v1"):
    conn.execute(
        "INSERT INTO songs (song_id, title, artist, year, source, tier, era_bucket) VALUES (?, ?, ?, ?, 'test', ?, ?)",
        (song_id, song_id, "Artist", 2020, tier, era),
    )
    conn.execute(
        """
        INSERT INTO features_song_lci (song_id, lyrics_id, axis_structure, axis_prosody, axis_rhyme,
         axis_lexical, axis_pov, axis_theme, LCI_lyric_v1_raw, LCI_lyric_v1_final_score, profile)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            song_id,
            f"{song_id}__lyr",
            axes["structure_fit"],
            axes["prosody_ttc_fit"],
            axes["rhyme_texture_fit"],
            axes["diction_style_fit"],
            axes["pov_fit"],
            axes["theme_fit"],
            score,
            score,
            profile,
        ),
    )
    conn.execute(
        """
        INSERT INTO features_ttc (song_id, ttc_seconds_first_chorus, estimation_method, profile)
        VALUES (?, ?, 'ttc_rule_based_v1', ?)
        """,
        (song_id, ttc_seconds, profile),
    )


def test_build_lane_norms(tmp_path):
    db_path = tmp_path / "norms.db"
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    axes_a = {
        "structure_fit": 0.5,
        "prosody_ttc_fit": 0.6,
        "rhyme_texture_fit": 0.4,
        "diction_style_fit": 0.7,
        "pov_fit": 0.5,
        "theme_fit": 0.3,
    }
    axes_b = {k: v + 0.1 for k, v in axes_a.items()}
    seed_lci_row(conn, "song_a", 1, "2015_2024", axes_a, 0.6, 30.0)
    seed_lci_row(conn, "song_b", 1, "2015_2024", axes_b, 0.7, 40.0)
    seed_lci_row(conn, "song_c", 2, "2015_2024", axes_a, 0.5, 20.0)
    conn.commit()

    norms = build_lane_norms(conn, profile="lci_us_pop_v1")
    lanes = {(lane["tier"], lane["era_bucket"]): lane for lane in norms["lanes"]}
    lane1 = lanes[(1, "2015_2024")]
    assert lane1["count"] == 2
    assert lane1["axes_mean"]["structure_fit"] == 0.55
    assert lane1["ttc_seconds_mean"] == 35.0
    lane2 = lanes[(2, "2015_2024")]
    assert lane2["count"] == 1
    conn.close()
