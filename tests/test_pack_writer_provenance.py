import json
from pathlib import Path

from tools import pack_writer


def test_build_pack_includes_provenance(tmp_path: Path):
    merged = {
        "source_audio": "song.wav",
        "duration_sec": 10.0,
        "tempo_bpm": 120.0,
        "key": "C",
        "mode": "major",
        "loudness_LUFS": -14.0,
        "energy": 0.5,
        "danceability": 0.5,
        "valence": 0.5,
        "provenance": {"track_id": "abc123", "git_sha": "deadbeef"},
    }
    features_meta = {
        "source_hash": "abc123dead",
        "config_fingerprint": "cfg123",
        "pipeline_version": "v1",
        "generated_utc": "2025-01-01T00:00:00Z",
        "sidecar_status": "used",
        "sidecar_attempts": 1,
        "sidecar_timeout_seconds": 60,
        "provenance": {"deps": {"numpy": "1.0.0"}},
    }

    pack = pack_writer.build_pack(merged, audio_name="song", anchor="00_core_modern", features_meta=features_meta)
    assert pack["provenance"]["track_id"] == "abc123"
    assert pack["provenance"]["git_sha"]
    assert pack["feature_pipeline_meta"]["source_hash"] == "abc123dead"
    assert pack["feature_pipeline_meta"]["pipeline_version"] == "v1"
    client_payload = pack_writer.build_client_helper_payload(pack)
    assert "provenance" in client_payload

