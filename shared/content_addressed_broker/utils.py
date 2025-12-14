from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_artifact(artifact_path: Path, manifest_path: Path) -> Tuple[bool, str | None, Dict[str, Any]]:
    """Return (ok, etag, manifest_dict) by comparing manifest sha256 to the artifact."""
    if not manifest_path.is_file() or not artifact_path.is_file():
        return False, None, {}
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception:
        return False, None, {}
    expected = (manifest.get("artifact") or {}).get("sha256")
    etag = (manifest.get("artifact") or {}).get("etag")
    actual = _hash_file(artifact_path)
    ok = expected == actual
    return ok, etag, manifest


def write_index_pointer(
    out_root: Path,
    track_id: str,
    config_hash: str,
    source_hash: str,
    etag: str | None,
    artifact_name: str,
    manifest_name: str,
) -> None:
    """Write a latest pointer for track_id → (config_hash, source_hash)."""
    idx_dir = out_root / "echo" / "index"
    idx_dir.mkdir(parents=True, exist_ok=True)
    pointer = {
        "track_id": track_id,
        "config_hash": config_hash,
        "source_hash": source_hash,
        "artifact": f"/echo/{config_hash}/{source_hash}/{artifact_name}",
        "manifest": f"/echo/{config_hash}/{source_hash}/{manifest_name}",
    }
    if etag:
        pointer["etag"] = etag
    (idx_dir / f"{track_id}.json").write_text(json.dumps(pointer))
