from pathlib import Path

import pytest

from security import files as sec_files
from security import paths as sec_paths
from security.config import CONFIG as SEC_CONFIG
from security import db as sec_db


def test_safe_join_allows_subpath(tmp_path):
    base = tmp_path
    target = sec_paths.safe_join(base, "child/file.txt")
    assert target.parent == base / "child"


def test_safe_join_blocks_traversal(tmp_path):
    with pytest.raises(sec_paths.PathValidationError):
        sec_paths.safe_join(tmp_path, "../escape.txt")


def test_ensure_allowed_extension_and_size(tmp_path):
    f = tmp_path / "a.wav"
    f.write_bytes(b"\0" * 10)
    # allowed
    sec_files.ensure_allowed_extension(str(f), {".wav", ".mp3"})
    sec_files.ensure_max_size(f, 100)
    # bad ext
    with pytest.raises(sec_files.FileValidationError):
        sec_files.ensure_allowed_extension(str(f), {".mp3"})
    # bad size
    with pytest.raises(sec_files.FileValidationError):
        sec_files.ensure_max_size(f, 1)


def test_ffprobe_format_rejects_disallowed(monkeypatch, tmp_path):
    """ffprobe format validation should reject disallowed formats."""
    from ma_audio_engine.adapters import audio_loader_adapter as loader

    fake_audio = tmp_path / "sample.wav"
    fake_audio.write_text("not real audio")

    class DummyResult:
        def __init__(self, stdout: str = ""):
            self.stdout = stdout

    def fake_run_safe(cmd, **kwargs):
        if "ffprobe" in cmd[0]:
            return DummyResult(stdout="video")
        raise RuntimeError("ffmpeg should not be invoked in this test")

    monkeypatch.setattr(loader.sec_subprocess, "run_safe", fake_run_safe)
    monkeypatch.setattr(loader, "_MAX_FFMPEG_DURATION_SEC", 1)
    with pytest.raises(RuntimeError):
        loader.load_audio_mono(str(fake_audio), sr=8000)


def test_validate_table_name():
    with pytest.raises(sec_db.DBSecurityError):
        sec_db.validate_table_name("bad-name")
    with pytest.raises(sec_db.DBSecurityError):
        sec_db.validate_table_name("drop table users")
    with pytest.raises(sec_db.DBSecurityError):
        sec_db.validate_table_name("foo", allowed={"bar"})
    assert sec_db.validate_table_name("spine_master_v1_lanes", allowed={"spine_master_v1_lanes"}) == "spine_master_v1_lanes"


def test_sandbox_scrub_payload():
    from ma_audio_engine.adapters import logging_adapter as la

    payload = {
        "tempo_beats_sec": [0.1, 0.2],
        "neighbors": [1, 2, 3],
        "comment": "x" * 50,
    }
    cfg = {"enabled": True, "drop_beats": True, "drop_neighbors": True, "max_chars": 10}
    scrubbed = la.sandbox_scrub_payload(payload, cfg)
    assert scrubbed["tempo_beats_sec"] is None
    assert scrubbed["neighbors"] == []
    assert scrubbed["comment"] == "x" * 10
