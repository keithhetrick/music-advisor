#!/usr/bin/env python3
"""
Lightweight JSON cache helpers for feature extraction.

Cache key = source_hash + config_fingerprint (hashed for brevity).
Writes are atomic (temp file + rename) to stay safe with parallel runs.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _cfg_hash(config_fingerprint: str) -> str:
    return hashlib.sha256(config_fingerprint.encode("utf-8")).hexdigest()[:12]


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


class _FileLock:
    """
    Minimal best-effort file lock using atomic create/unlink.
    Non-blocking contention safety for parallel writers; reads remain lock-free.
    """

    def __init__(self, path: Path, timeout: float = 5.0, poll: float = 0.05) -> None:
        self.path = path
        self.timeout = timeout
        self.poll = poll

    def __enter__(self):
        start = time.time()
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return self
            except FileExistsError:
                if (time.time() - start) >= self.timeout:
                    raise TimeoutError(f"Could not acquire lock {self.path}")
                time.sleep(self.poll)

    def __exit__(self, exc_type, exc, tb):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass


class FeatureCache:
    def __init__(self, cache_dir: Optional[str] = None) -> None:
        self.cache_dir = Path(cache_dir or ".ma_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, source_hash: str, config_fingerprint: str) -> Path:
        return self.cache_dir / f"{source_hash}_{_cfg_hash(config_fingerprint)}.json"

    def load(self, source_hash: str, config_fingerprint: str, source_mtime: float) -> Optional[Dict[str, Any]]:
        path = self._path_for(source_hash, config_fingerprint)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
        except Exception:
            return None

        cached_mtime = data.get("source_mtime")
        if cached_mtime is None:
            return None
        if abs(float(cached_mtime) - float(source_mtime)) > 1e-3:
            return None

        return data

    def store(self, source_hash: str, config_fingerprint: str, payload: Dict[str, Any]) -> Path:
        path = self._path_for(source_hash, config_fingerprint)
        lock_path = path.with_suffix(path.suffix + ".lock")
        with _FileLock(lock_path):
            _atomic_write_json(path, payload)
        return path

    def gc(self) -> Dict[str, int]:
        """
        Best-effort cache cleanup:
        - Remove temp files.
        - Remove unreadable/corrupt entries.
        Note: cannot check source existence because paths are not stored in cache filenames.
        """
        removed = 0
        temp_removed = 0
        for f in self.cache_dir.glob("*.tmp"):
            f.unlink(missing_ok=True)
            temp_removed += 1
        for f in self.cache_dir.glob("*.json"):
            try:
                json.loads(f.read_text())
            except Exception:
                f.unlink(missing_ok=True)
                removed += 1
        return {"temp_removed": temp_removed, "entries_removed": removed}
