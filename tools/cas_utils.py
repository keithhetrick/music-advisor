"""
Lightweight helpers for content-addressed storage (CAS) of Historical Echo artifacts.

These utilities are intentionally dependency-light and stable so they can be reused by
runner/broker/validation code without pulling in heavy stacks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_bytes(payload: Any) -> bytes:
    """
    Return canonical JSON bytes for hashing/ETag calculation.

    - Sorted keys
    - No trailing spaces (compact separators)
    - UTF-8 encoding; allow non-ASCII content without escaping
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Compute a hex-encoded sha256 digest for the given bytes."""
    return hashlib.sha256(data).hexdigest()


def build_cas_path(root: Path, config_hash: str, source_hash: str, filename: str) -> Path:
    """
    Build a CAS path with the canonical shape:
      <root>/echo/<config_hash>/<source_hash>/<filename>
    """
    return Path(root) / "echo" / config_hash / source_hash / filename
