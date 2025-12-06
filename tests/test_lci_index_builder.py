import json
import sqlite3
from types import SimpleNamespace
from pathlib import Path

from tools.lci_index_builder import (
    build_calibration,
    compute_lci_for_song,
    load_calibration,
    run_score_songs,
)
from ma_lyrics_engine.schema import ensure_schema
from ma_lyrics_engine.ingest import upsert_lyrics, upsert_song
from ma_lyrics_engine.features import write_song_features
from ma_lyrics_engine.export import export_bridge_payload


def _insert_song_with_features(conn: sqlite3.Connection, song_id: str, lyrics_id: str, overrides=None) -> None:
    base_features = {
        "song_id": song_id,
        "lyrics_id": lyrics_id,
        "verse_count": 2,
        "pre_count": 1,
        "chorus_count": 2,
        "bridge_count": 0,
        "outro_count": 0,
        "section_pattern": "V-P-C-V-C",
        "avg_words_per_line": 10.0,
        "avg_syllables_per_line": 12.0,
        "lexical_diversity": 0.55,
        "repetition_rate": 0.2,
        "hook_density": 0.3,
        "sentiment_mean": 0.1,
        "sentiment_std": 0.05,
        "pov_first": 0.05,
        "pov_second": 0.03,
        "pov_third": 0.02,
        "explicit_fraction": 0.0,
        "rhyme_density": 0.4,
        "internal_rhyme_density": 0.1,
        "concreteness": 0.5,
        "theme_love": 0.2,
        "theme_heartbreak": 0.1,
        "theme_empowerment": 0.05,
        "theme_nostalgia": 0.05,
        "theme_flex": 0.02,
        "theme_spiritual": 0.03,
        "theme_family": 0.01,
        "theme_small_town": 0.04,
        "syllable_density": 1.0,
        "tempo_bpm": 120.0,
        "duration_sec": 180.0,
    }
    if overrides:
        base_features.update(overrides)
    upsert_song(conn, song_id, "Title", "Artist", 2024, None, None, "test")
    upsert_lyrics(conn, lyrics_id, song_id, "raw", "clean", "test")
    write_song_features(conn, base_features)


def test_score_songs_writes_lci(tmp_path):
    db_path = tmp_path / "lci.db"
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    _insert_song_with_features(conn, "song_one", "song_one__lyr")
    _insert_song_with_features(conn, "song_two", "song_two__lyr", {"repetition_rate": 0.4, "hook_density": 0.6})
    conn.close()

    calibration = {
        "version": "LCI_lyric_v1",
        "profile": "test",
        "axes": {
            axis: {"mu": 0.5, "sigma": 0.2, "clip": 3.0, "weight": 1.0}
            for axis in ("structure", "prosody", "rhyme", "lexical", "pov", "theme")
        },
        "aggregation": {"method": "weighted_mean", "target_mu": 0.5, "target_sigma": 0.15},
    }
    calib_path = tmp_path / "calib.json"
    calib_path.write_text(json.dumps(calibration), encoding="utf-8")

    args = SimpleNamespace(
        db=str(db_path),
        calibration=str(calib_path),
        profile="test",
        song_id=None,
        limit=None,
        cmd="score-songs",
    )
    logs = []
    run_score_songs(args, logs.append)

    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT axis_structure, axis_prosody, axis_rhyme, axis_lexical, axis_pov, axis_theme, LCI_lyric_v1_final_score FROM features_song_lci")
    rows = cur.fetchall()
    assert len(rows) == 2
    for row in rows:
        assert all(0.0 <= val <= 1.0 for val in row)
    conn.close()


def test_compute_and_build_calibration_roundtrip(tmp_path):
    db_path = tmp_path / "lci.db"
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    _insert_song_with_features(conn, "song_core", "song_core__lyr")
    conn.commit()

    calib_out = tmp_path / "built_calib.json"
    logs = []
    calibration = build_calibration(conn, core_csv=None, profile="test_profile", out_path=calib_out, log=logs.append)
    assert calib_out.exists()
    parsed = load_calibration(calib_out)
    assert parsed["version"] == "LCI_lyric_v1"
    assert set(parsed["axes"].keys()) == {
        "structure_fit",
        "prosody_ttc_fit",
        "rhyme_texture_fit",
        "diction_style_fit",
        "pov_fit",
        "theme_fit",
    }
    assert calibration["aggregation"]["target_mu"] == parsed["aggregation"]["target_mu"]

    ok = compute_lci_for_song(conn, song_id="song_core", profile="test_profile", calibration=parsed, log=logs.append)
    assert ok
    cur = conn.execute("SELECT LCI_lyric_v1_final_score FROM features_song_lci WHERE song_id=?", ("song_core",))
    row = cur.fetchone()
    assert row is not None
    assert 0.0 <= row[0] <= 1.0
    payload = export_bridge_payload(conn, "song_core", limit=1)
    assert payload["count"] == 1
    lci = payload["items"][0].get("lyric_confidence_index")
    assert lci is not None
    assert set(lci["axes"].keys()) == {
        "structure_fit",
        "prosody_ttc_fit",
        "rhyme_texture_fit",
        "diction_style_fit",
        "pov_fit",
        "theme_fit",
    }
    assert "score" in lci
    assert lci.get("calibration_profile") == parsed.get("calibration_profile")
    conn.close()
