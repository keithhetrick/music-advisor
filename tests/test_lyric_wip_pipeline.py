import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from tools import lyric_wip_pipeline
from ma_lyrics_engine.schema import ensure_schema


def test_wip_pipeline_runs_stt_and_neighbors(tmp_path, monkeypatch):
    db_path = tmp_path / "lyric.db"
    out_dir = tmp_path / "out"

    # Stub STT pieces to avoid real audio work
    transcript = {"text": "", "segments": [{"text": "Alpha line"}, {"text": "Beta line"}]}
    monkeypatch.setattr(
        "tools.lyric_stt_sidecar.transcribe_audio",
        lambda path, log: transcript,
    )
    monkeypatch.setattr(
        "tools.lyric_stt_sidecar.extract_vocals",
        lambda path, log: Path(path),
    )

    # Seed a corpus song with a vector for neighbors
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    conn.execute("INSERT INTO songs (song_id, title, artist, year, source) VALUES ('corpus_song', 'Title', 'Artist', 2020, 'test')")
    conn.execute("INSERT INTO features_song_vector (song_id, vector) VALUES ('corpus_song', '[0.5, 0.1]')")
    conn.commit()
    conn.close()

    args = SimpleNamespace(
        audio=str(tmp_path / "dummy.wav"),
        song_id="wip_song",
        title="WIP Title",
        artist="Tester",
        year=2024,
        db=str(db_path),
        out_dir=str(out_dir),
        limit=5,
        distance="cosine",
        skip_neighbors=False,
        no_vocal_separation=True,
        concreteness_lexicon=None,
        transcript_file=None,
        segments_file=None,
        run_alt_stt=False,
        lci_calibration="shared/calibration/lci_calibration_us_pop_v1.json",
        lci_profile="us_pop",
        skip_lci=False,
        ttc_profile_label="ttc_us_pop_v1",
        ttc_seconds_per_section=12.0,
        ttc_profile_path="shared/calibration/ttc_profile_us_pop_v1.json",
    )
    # create dummy audio
    Path(args.audio).write_bytes(b"fake-audio")

    logs = []
    lyric_wip_pipeline.run_pipeline(args, logs.append)

    # Bridge JSON exists
    bridge_path = out_dir / "wip_song_bridge.json"
    assert bridge_path.exists()
    bridge = json.loads(bridge_path.read_text())
    assert bridge["count"] == 1
    assert "lyric_confidence_index" in bridge["items"][0]
    assert "ttc_profile" in bridge["items"][0]

    # Neighbors JSON exists
    neighbors_path = out_dir / "wip_song_neighbors.json"
    assert neighbors_path.exists()
    neighbors = json.loads(neighbors_path.read_text())
    assert neighbors["count"] >= 0
