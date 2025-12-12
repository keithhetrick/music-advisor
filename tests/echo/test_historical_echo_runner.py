from __future__ import annotations

import json
from pathlib import Path

from tools.cas_utils import canonical_json_bytes, sha256_hex
from tools.hci.historical_echo_runner import run


def _fake_probe(**_: str) -> dict:
    return {
        "neighbors": [
            {"year": 2001, "artist": "Test", "title": "Track", "distance": 0.1, "tier": "tier1_modern"}
        ],
        "decade_counts": {"2000–2009": 1},
        "primary_decade": "2000–2009",
        "primary_decade_neighbor_count": 1,
        "top_neighbor": {"year": 2001, "artist": "Test", "title": "Track", "distance": 0.1, "tier": "tier1_modern"},
    }


def test_runner_writes_canonical_artifacts(tmp_path: Path) -> None:
    features = {"tempo_bpm": 120.0, "energy": 0.5, "valence": 0.5}
    features_path = tmp_path / "song.features.json"
    features_path.write_text(json.dumps(features))

    out = run(
        features_path=features_path,
        out_root=tmp_path / "cas",
        track_id="song-1",
        run_id="run-123",
        config_hash="cfg-abc",
        db_hash="db-xyz",
        probe_fn=_fake_probe,
    )

    artifact = json.loads(out["artifact"].read_text())
    manifest = json.loads(out["manifest"].read_text())

    assert artifact["track_id"] == "song-1"
    assert artifact["config_hash"] == "cfg-abc"
    assert artifact["db_hash"] == "db-xyz"
    assert artifact["neighbors"][0]["title"] == "Track"

    artifact_bytes = canonical_json_bytes(artifact)
    assert manifest["artifact"]["sha256"] == sha256_hex(artifact_bytes)
    assert manifest["artifact"]["path"] == "historical_echo.json"
