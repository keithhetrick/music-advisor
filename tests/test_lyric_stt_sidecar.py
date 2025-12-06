from types import SimpleNamespace
import json
from pathlib import Path
import sqlite3

from tools import lyric_stt_sidecar as sidecar
from tools.lyric_intel_engine import export_bridge_payload


def test_process_wip_writes_lyrics_and_features(tmp_path, monkeypatch):
    audio_path = tmp_path / "dummy.wav"
    audio_path.write_bytes(b"fake-audio")
    db_path = tmp_path / "lyric_intel.db"

    transcript = {
        "text": "hello world",
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "First line"},
            {"start": 1.0, "end": 2.0, "text": "Second line"},
        ],
    }
    monkeypatch.setattr(sidecar, "transcribe_audio", lambda path, log: transcript)
    monkeypatch.setattr(sidecar, "extract_vocals", lambda path, log: path)

    args = SimpleNamespace(
        audio=str(audio_path),
        song_id="test_song_123",
        title="Test Song",
        artist="Tester",
        year=2024,
        db=str(db_path),
        out=None,
        no_vocal_separation=True,
        concreteness_lexicon=None,
        transcript_file=None,
        segments_file=None,
        run_alt_stt=False,
        lci_calibration="shared/calibration/lci_calibration_us_pop_v1.json",
        skip_lci=False,
        cmd="process-wip",
    )
    logs = []
    sidecar.process_wip(args, logs.append)

    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT source FROM lyrics WHERE song_id=?", (args.song_id,))
    row = cur.fetchone()
    assert row is not None and row[0] == "wip_stt"

    cur = conn.execute("SELECT song_id FROM features_song WHERE song_id=?", (args.song_id,))
    assert cur.fetchone() is not None

    payload = export_bridge_payload(conn, args.song_id, limit=1)
    assert payload["count"] == 1
    lci = payload["items"][0].get("lyric_confidence_index")
    assert lci is not None
    assert "score" in lci

    conn.close()


def test_process_wip_uses_transcript_file(tmp_path, monkeypatch):
    audio_path = tmp_path / "dummy.wav"
    audio_path.write_bytes(b"fake-audio")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("Line one\nLine two", encoding="utf-8")
    db_path = tmp_path / "lyric_intel.db"

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("transcribe_audio should not be called when transcript_file is provided")

    monkeypatch.setattr(sidecar, "transcribe_audio", fail_if_called)
    monkeypatch.setattr(sidecar, "extract_vocals", fail_if_called)

    args = SimpleNamespace(
        audio=str(audio_path),
        song_id="test_song_transcript",
        title="Test Song",
        artist="Tester",
        year=2024,
        db=str(db_path),
        out=None,
        no_vocal_separation=True,
        concreteness_lexicon=None,
        transcript_file=str(transcript_path),
        segments_file=None,
        run_alt_stt=False,
        lci_calibration=None,
        skip_lci=True,
        cmd="process-wip",
    )
    logs = []
    sidecar.process_wip(args, logs.append)

    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT raw_text, source FROM lyrics WHERE song_id=?", (args.song_id,))
    row = cur.fetchone()
    assert row is not None
    assert "Line one" in row[0]
    assert row[1] == "wip_stt"
    conn.close()


def test_process_wip_uses_segments_file(tmp_path, monkeypatch):
    audio_path = tmp_path / "dummy.wav"
    audio_path.write_bytes(b"fake-audio")
    segments_path = tmp_path / "segments.json"
    segments_path.write_text(
        '[{"start":0,"end":1,"text":"Alpha"}, {"start":1,"end":2,"text":"Beta"}]',
        encoding="utf-8",
    )
    db_path = tmp_path / "lyric_intel.db"

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("transcribe_audio should not be called when segments_file is provided")

    monkeypatch.setattr(sidecar, "transcribe_audio", fail_if_called)
    monkeypatch.setattr(sidecar, "extract_vocals", fail_if_called)

    args = SimpleNamespace(
        audio=str(audio_path),
        song_id="test_song_segments",
        title="Test Song",
        artist="Tester",
        year=2024,
        db=str(db_path),
        out=None,
        no_vocal_separation=True,
        concreteness_lexicon=None,
        transcript_file=None,
        segments_file=str(segments_path),
        run_alt_stt=False,
        lci_calibration=None,
        skip_lci=True,
        cmd="process-wip",
    )
    logs = []
    sidecar.process_wip(args, logs.append)

    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT raw_text, source FROM lyrics WHERE song_id=?", (args.song_id,))
    row = cur.fetchone()
    assert row is not None
    assert "Alpha" in row[0]
    assert "Beta" in row[0]
    assert row[1] == "wip_stt"
    conn.close()


def test_process_wip_prefers_alt_stt(tmp_path, monkeypatch):
    audio_path = tmp_path / "dummy.wav"
    audio_path.write_bytes(b"fake-audio")
    db_path = tmp_path / "lyric_intel.db"

    # primary returns short text, alt returns longer
    monkeypatch.setattr(
        sidecar,
        "transcribe_audio",
        lambda path, log: {"text": "", "segments": [{"text": "short"}]},
    )
    monkeypatch.setattr(
        sidecar,
        "transcribe_audio_alt",
        lambda path, log: {"text": "", "segments": [{"text": "long alt line one"}, {"text": "two"}]},
    )
    monkeypatch.setattr(sidecar, "extract_vocals", lambda path, log: path)

    args = SimpleNamespace(
        audio=str(audio_path),
        song_id="test_song_alt",
        title="Test Song",
        artist="Tester",
        year=2024,
        db=str(db_path),
        out=None,
        no_vocal_separation=True,
        concreteness_lexicon=None,
        transcript_file=None,
        segments_file=None,
        run_alt_stt=True,
        lci_calibration=None,
        skip_lci=True,
        cmd="process-wip",
    )
    logs = []
    sidecar.process_wip(args, logs.append)

    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT raw_text, source FROM lyrics WHERE lyrics_id=?", (f"{args.song_id}__wip_stt",))
    row = cur.fetchone()
    assert row is not None
    assert "long alt line one" in row[0]
    cur = conn.execute("SELECT raw_text, source FROM lyrics WHERE lyrics_id=?", (f"{args.song_id}__wip_stt_alt",))
    alt_row = cur.fetchone()
    assert alt_row is not None
    assert alt_row[1] == "wip_stt_alt"
    conn.close()


def test_process_wip_optionally_computes_lci(tmp_path, monkeypatch):
    audio_path = tmp_path / "dummy.wav"
    audio_path.write_bytes(b"fake-audio")
    db_path = tmp_path / "lyric_intel.db"

    transcript = {
        "text": "",
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "Alpha line"},
            {"start": 1.0, "end": 2.0, "text": "Beta line"},
        ],
    }
    monkeypatch.setattr(sidecar, "transcribe_audio", lambda path, log: transcript)
    monkeypatch.setattr(sidecar, "extract_vocals", lambda path, log: path)

    calib_path = tmp_path / "calib.json"
    calib_path.write_text(
        json.dumps(
            {
                "version": "LCI_lyric_v1",
                "profile": "test",
                "axes": {
                    axis: {"mu": 0.3, "sigma": 0.2, "clip": 3.0, "weight": 1.0}
                    for axis in ("structure", "prosody", "rhyme", "lexical", "pov", "theme")
                },
                "aggregation": {"method": "weighted_mean", "target_mu": 0.5, "target_sigma": 0.2},
            }
        ),
        encoding="utf-8",
    )

    args = SimpleNamespace(
        audio=str(audio_path),
        song_id="test_song_lci",
        title="Test Song",
        artist="Tester",
        year=2024,
        db=str(db_path),
        out=None,
        no_vocal_separation=True,
        concreteness_lexicon=None,
        transcript_file=None,
        segments_file=None,
        run_alt_stt=False,
        lci_calibration=str(calib_path),
        lci_profile="test",
        cmd="process-wip",
    )
    logs = []
    sidecar.process_wip(args, logs.append)

    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT LCI_lyric_v1_final_score FROM features_song_lci WHERE song_id=?", (args.song_id,)
    )
    row = cur.fetchone()
    assert row is not None
    assert 0.0 <= row[0] <= 1.0
    conn.close()
