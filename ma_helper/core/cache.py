"""Hash-based cache helpers used by test/run orchestration."""
from __future__ import annotations

import hashlib
import os
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .env import ARTIFACT_DIR, CACHE_DIR, CACHE_FILE, CACHE_ENABLED


def load_cache(cache_file: Path = CACHE_FILE) -> Dict[str, Any]:
    if not CACHE_ENABLED or not cache_file.exists():
        return {}
    try:
        return json.loads(cache_file.read_text())
    except Exception:
        return {}


def save_cache(cache: Dict[str, Any], cache_dir: Path = CACHE_DIR, cache_file: Path = CACHE_FILE) -> None:
    if not CACHE_ENABLED:
        return
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=2))
    except Exception as exc:
        print(f"[ma] warning: could not persist cache ({exc})", file=sys.stderr)


def write_artifact(project, target: str, info: Dict[str, Any], artifact_dir: Path = ARTIFACT_DIR) -> None:
    if not CACHE_ENABLED:
        return
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        meta = {"project": project.name, "target": target, "hash": info.get("hash"), "ts": time.time()}
        path = artifact_dir / f"{project.name}_{target}.json"
        path.write_text(json.dumps(meta, indent=2))
    except Exception:
        pass


def _hash_dir(paths: List[Path]) -> str:
    m = hashlib.sha256()
    for path in sorted(paths):
        if path.is_file():
            try:
                m.update(path.read_bytes())
            except Exception:
                pass
        elif path.is_dir():
            for sub in sorted(path.rglob("*")):
                if sub.is_file():
                    try:
                        m.update(sub.read_bytes())
                    except Exception:
                        pass
    return m.hexdigest()[:12]


def hash_project(project) -> str:
    paths = [Path(project.path)]
    for test_dir in project.tests:
        paths.append(Path(test_dir))
    return _hash_dir(paths)


def should_skip_cached(project, target: str, cache_mode: str) -> Tuple[bool, Dict[str, Any]]:
    if cache_mode == "off":
        return False, {}
    cache = load_cache()
    key = f"{project.name}:{target}"
    cached = cache.get(key)
    current_hash = hash_project(project)
    if cache_mode == "restore-only":
        if cached and cached.get("hash") == current_hash and cached.get("status") == 0:
            print(f"[ma] cache hit: {project.name} {target} (restore-only)")
            return True, cached
        return False, {"hash": current_hash}
    if cached and cached.get("hash") == current_hash and cached.get("status") == 0:
        print(f"[ma] cache hit: {project.name} {target}")
        return True, cached
    return False, {"hash": current_hash}


def update_cache(project, target: str, info: Dict[str, Any], cache_mode: str) -> None:
    if cache_mode == "off":
        return
    cache = load_cache()
    key = f"{project.name}:{target}"
    cache[key] = info
    save_cache(cache)
    if info.get("status") == 0:
        write_artifact(project, target, info)
