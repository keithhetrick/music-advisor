from __future__ import annotations

import json
from pathlib import Path

from tools.cas_utils import canonical_json_bytes, sha256_hex
from tools.task_conductor.echo_utils import validate_artifact, write_index_pointer


def test_validate_artifact_round_trip(tmp_path: Path) -> None:
    artifact_payload = {"hello": "world"}
    artifact_path = tmp_path / "historical_echo.json"
    artifact_bytes = canonical_json_bytes(artifact_payload)
    artifact_path.write_bytes(artifact_bytes)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact": {
                    "path": "historical_echo.json",
                    "sha256": sha256_hex(artifact_bytes),
                    "etag": sha256_hex(artifact_bytes),
                    "size": len(artifact_bytes),
                }
            }
        )
    )
    ok, etag, manifest = validate_artifact(artifact_path, manifest_path)
    assert ok is True
    assert etag == manifest["artifact"]["sha256"]


def test_write_index_pointer(tmp_path: Path) -> None:
    idx = write_index_pointer(tmp_path, "song-1", "cfg", "src", "etag123")
    payload = json.loads(idx.read_text())
    assert payload["track_id"] == "song-1"
    assert payload["config_hash"] == "cfg"
    assert payload["source_hash"] == "src"
    assert payload["etag"] == "etag123"
