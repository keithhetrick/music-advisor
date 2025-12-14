"""
Shared helpers for the Historical Echo TaskConductor components.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from tools.cas_utils import canonical_json_bytes, sha256_hex


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    return json.loads(manifest_path.read_text())


def validate_artifact(artifact_path: Path, manifest_path: Path) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Validate that artifact sha matches manifest; returns (ok, etag, manifest)."""
    manifest = load_manifest(manifest_path)
    expected_sha = (manifest.get("artifact") or {}).get("sha256")
    if not expected_sha:
        return False, None, manifest
    if not artifact_path.is_file():
        return False, None, manifest
    sha = sha256_hex(artifact_path.read_bytes())
    return sha == expected_sha, expected_sha, manifest


def write_index_pointer(cas_root: Path, track_id: str, config_hash: str, source_hash: str, etag: str) -> Path:
    """Write a small pointer file for 'latest' resolution."""
    payload = {
        "track_id": track_id,
        "config_hash": config_hash,
        "source_hash": source_hash,
        "artifact": f"/echo/{config_hash}/{source_hash}/historical_echo.json",
        "manifest": f"/echo/{config_hash}/{source_hash}/manifest.json",
        "etag": etag,
    }
    index_path = cas_root / "echo" / "index" / f"{track_id}.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_bytes(canonical_json_bytes(payload))
    return index_path
