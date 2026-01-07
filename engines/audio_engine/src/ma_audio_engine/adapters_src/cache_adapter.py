"""
Cache adapter: thin wrapper around FeatureCache so cache backend can be swapped without touching callers.

Supports:
- disk (default): on-disk FeatureCache
- noop: no-op cache (always miss), useful for sandbox/batch runs without touching disk

Defaults can be overridden via ``config/cache.json`` (`default_cache_dir`, `default_backend`).
No env flags are consumed here; callers pass backend/dir explicitly or rely on config defaults.

Usage:
- `cache = get_cache(cache_dir=".ma_cache", backend="disk"); cache.save(...); cache.load(...)`
- For sandbox runs: `cache = get_cache(backend="noop")` to bypass disk I/O.

Notes:
- Side effects: writes to disk when backend=disk; noop backend is pure.
- Unknown backend strings fall back to disk; missing cache_dir forces noop to avoid errors.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from shared.ma_utils.cache_utils import FeatureCache

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "cache.json"
_DEFAULT_CACHE_DIR = None
_DEFAULT_BACKEND = "disk"

try:
    if _CFG_PATH.exists():
        data = json.loads(_CFG_PATH.read_text())
        if isinstance(data, dict):
            if isinstance(data.get("default_cache_dir"), str):
                _DEFAULT_CACHE_DIR = data["default_cache_dir"]
            if isinstance(data.get("default_backend"), str):
                _DEFAULT_BACKEND = data["default_backend"]
except Exception:
    # Optional config; fall back silently.
    pass


class CacheAdapter:
    """Cache facade that falls back to noop when the backend is unavailable or disabled."""
    def __init__(self, cache_dir: Optional[str], backend: str = "disk"):
        cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        backend = (backend or _DEFAULT_BACKEND or "disk").lower()
        if backend not in ("disk", "noop"):
            backend = "disk"
        if backend == "disk" and not cache_dir:
            # No cache dir available -> noop to avoid errors.
            backend = "noop"
        self._backend = backend
        self._cache = FeatureCache(cache_dir) if backend == "disk" else None

    def load(self, *, source_hash: str, config_fingerprint: str, source_mtime: float) -> Optional[Dict[str, Any]]:
        if self._backend == "noop":
            return None
        return self._cache.load(source_hash=source_hash, config_fingerprint=config_fingerprint, source_mtime=source_mtime)

    def save(self, *, source_hash: str, config_fingerprint: str, payload: Dict[str, Any], source_mtime: float) -> None:
        if self._backend == "noop":
            return
        # FeatureCache does not require source_mtime; it is expected to be inside payload if needed.
        self._cache.store(source_hash=source_hash, config_fingerprint=config_fingerprint, payload=payload)

    # Backwards-compat alias used by legacy callers.
    def store(self, *, source_hash: str, config_fingerprint: str, payload: Dict[str, Any], source_mtime: float) -> None:
        self.save(
            source_hash=source_hash,
            config_fingerprint=config_fingerprint,
            payload=payload,
            source_mtime=source_mtime,
        )

def gc(self) -> Dict[str, int]:
    """
        Garbage collect the underlying cache when supported.
        Returns a stats dict for consistency.
        Side effects: may delete temp/corrupt cache entries when backend=disk; noop backend returns zeros.
    """
    if self._backend == "noop" or not self._cache:
        return {"temp_removed": 0, "entries_removed": 0}
    return self._cache.gc()


def get_cache(cache_dir: Optional[str] = None, backend: str = "disk") -> CacheAdapter:
    """
    Factory to keep callers decoupled from the concrete cache implementation.
    """
    return CacheAdapter(cache_dir=cache_dir, backend=backend)
