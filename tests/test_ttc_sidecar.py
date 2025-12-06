from types import SimpleNamespace
import json
import sqlite3

from tools.ttc_sidecar import run_estimate
from ma_lyric_engine.schema import ensure_schema
from ma_lyric_engine.export import export_bridge_payload


def test_ttc_sidecar_writes_features(tmp_path):
    db_path = tmp_path / "ttc.db"
    args = SimpleNamespace(
        db=str(db_path),
        song_id="song_ttc",
        section_pattern="V-P-C-V-C",
        profile="stub",
        out=None,
        cmd="estimate",
        seconds_per_section=12.0,
        ttc_profile=None,
    )
    logs = []
    run_estimate(args, logs.append)

    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT ttc_seconds_first_chorus, ttc_bar_position_first_chorus, estimation_method FROM features_ttc WHERE song_id=?", ("song_ttc",))
    row = cur.fetchone()
    assert row is not None
    # pattern V-P-C -> chorus at index 2 -> seconds_per_section=12 fallback
    assert row[0] == 24.0
    assert row[1] is None
    assert row[2] == "ttc_rule_based_v1"
    payload_cur = conn.execute("SELECT 1 FROM features_song")
    conn.close()


def test_ttc_export_in_bridge(tmp_path):
    db_path = tmp_path / "ttc.db"
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    # seed a song with pattern and tempo/duration
    conn.execute(
        "INSERT INTO songs (song_id, title, artist, year, source) VALUES (?, ?, ?, ?, 'test')",
        ("song_ttc_export", "Title", "Artist", 2024),
    )
    conn.execute(
        """
        INSERT INTO features_song (song_id, lyrics_id, verse_count, pre_count, chorus_count, bridge_count, outro_count,
         section_pattern, avg_words_per_line, avg_syllables_per_line, lexical_diversity, repetition_rate, hook_density,
         sentiment_mean, sentiment_std, pov_first, pov_second, pov_third, explicit_fraction, rhyme_density,
         internal_rhyme_density, concreteness, theme_love, theme_heartbreak, theme_empowerment, theme_nostalgia,
         theme_flex, theme_spiritual, theme_family, theme_small_town, syllable_density, tempo_bpm, duration_sec)
        VALUES (?, ?, 1,0,2,0,0, ?, 8, 10, 0.5, 0.1, 0.2, 0,0,0,0,0,0,0.1,0.0,0.5,0,0,0,0,0,0,0,0,0.5,120,180)
        """,
        ("song_ttc_export", "song_ttc_export__lyr", "V-C-C"),
    )
    conn.execute(
        "INSERT INTO features_song_vector (song_id, vector) VALUES (?, ?)",
        ("song_ttc_export", json.dumps([0.1, 0.2])),
    )
    conn.commit()
    conn.close()

    args = SimpleNamespace(
        db=str(db_path),
        song_id="song_ttc_export",
        section_pattern=None,
        profile="stub",
        out=None,
        cmd="estimate",
        seconds_per_section=12.0,
        ttc_profile=None,
    )
    logs = []
    run_estimate(args, logs.append)

    conn = sqlite3.connect(db_path)
    payload = export_bridge_payload(conn, "song_ttc_export", limit=1)
    assert payload["count"] == 1
    ttc = payload["items"][0].get("ttc_profile")
    assert ttc is not None
    assert ttc["estimation_method"] == "ttc_rule_based_v1"
    assert ttc["ttc_seconds_first_chorus"] is not None
    conn.close()
