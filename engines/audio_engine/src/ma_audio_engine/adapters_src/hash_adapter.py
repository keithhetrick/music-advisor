"""
Hash adapter: allow swapping hash algorithm/chunk size via config/hash.json.

Defaults:
- algorithm: sha256
- chunk_size: 64KiB

Config:
- file: config/hash.json (keys: algorithm, chunk_size)
- env: none (callers pass overrides directly if needed).

Usage:
- `algo, chunk = get_hash_params()` for defaults from config.
- `digest = hash_file(path, algorithm="sha256", chunk_size=1<<16)`
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Tuple

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "hash.json"
_DEFAULT_ALGO = "sha256"
_DEFAULT_CHUNK = 1 << 16

try:
    if _CFG_PATH.exists():
        data = json.loads(_CFG_PATH.read_text())
        if isinstance(data, dict):
            algo = data.get("algorithm")
            if isinstance(algo, str) and algo.strip():
                _DEFAULT_ALGO = algo.strip().lower()
            chunk = data.get("chunk_size")
            if isinstance(chunk, int) and chunk > 0:
                _DEFAULT_CHUNK = chunk
except Exception:
    # Optional config; fall back silently.
    pass


def get_hash_params() -> Tuple[str, int]:
    """Return the effective (algorithm, chunk_size) after applying config overrides."""
    return _DEFAULT_ALGO, _DEFAULT_CHUNK


def hash_file(path: str, algorithm: str = None, chunk_size: int = None) -> str:
    """Hash a file with the given algorithm/chunk size (falls back to sha256 on errors)."""
    algo = (algorithm or _DEFAULT_ALGO).lower()
    chunk = chunk_size or _DEFAULT_CHUNK
    try:
        h = hashlib.new(algo)
    except Exception:
        h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk_bytes = f.read(chunk)
            if not chunk_bytes:
                break
            h.update(chunk_bytes)
    return h.hexdigest()
