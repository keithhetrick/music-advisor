"""
In-memory cache plugin for testing; does not persist to disk.
"""
from __future__ import annotations

from typing import Optional, Dict
import time

from adapters.cache_adapter import CacheAdapter


class _MemoryCache(CacheAdapter):
    def __init__(self):
        self._store: Dict[str, dict] = {}

    def load(self, source_hash: str, config_fingerprint: str, source_mtime: Optional[float] = None):
        key = f"{source_hash}:{config_fingerprint}"
        entry = self._store.get(key)
        if entry and source_mtime is not None:
            if entry.get("source_mtime") != source_mtime:
                return None
        return entry

    def store(self, source_hash: str, config_fingerprint: str, payload: dict, source_mtime: Optional[float] = None):
        key = f"{source_hash}:{config_fingerprint}"
        self._store[key] = dict(payload)
        if source_mtime is not None:
            self._store[key]["source_mtime"] = source_mtime
        self._store[key]["stored_at"] = time.time()


def factory(cache_dir: Optional[str] = None, backend: Optional[str] = None) -> CacheAdapter:
    return _MemoryCache()
