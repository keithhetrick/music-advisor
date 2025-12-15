"""Cache stats/clear/explain commands."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, Any

from ma_helper.core.cache import CACHE_DIR, CACHE_FILE


def cache_stats(as_json: bool = False) -> int:
    data: Dict[str, Any] = {}
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
        except Exception:
            data = {}
    entries = data
    stats = {"entries": len(entries), "path": str(CACHE_DIR)}
    if as_json:
        print(json.dumps(stats, indent=2))
        return 0
    print(f"[ma] cache dir: {CACHE_DIR}")
    print(f"[ma] entries : {len(entries)}")
    return 0


def cache_clear() -> int:
    try:
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
        print(f"[ma] cache cleared: {CACHE_DIR}")
        return 0
    except Exception as exc:
        print(f"[ma] failed to clear cache: {exc}")
        return 1


def cache_explain(task: str, as_json: bool = False) -> int:
    if not CACHE_FILE.exists():
        print("[ma] no cache file found.")
        return 1
    try:
        data = json.loads(CACHE_FILE.read_text())
    except Exception as exc:
        print(f"[ma] could not read cache: {exc}")
        return 1
    entries = data
    entry = entries.get(task)
    if not entry:
        print(f"[ma] no cache entry for task '{task}'")
        return 1
    if as_json:
        print(json.dumps(entry, indent=2))
        return 0
    print(f"[ma] cache entry: {task}")
    print(f"- hash      : {entry.get('hash')}")
    print(f"- inputs    : {', '.join(entry.get('inputs', [])) or 'none'}")
    print(f"- outputs   : {', '.join(entry.get('outputs', [])) or 'none'}")
    print(f"- env       : {', '.join(entry.get('env', [])) or 'none'}")
    print(f"- args      : {entry.get('args')}")
    print(f"- created   : {entry.get('created')}")
    print(f"- cache path: {entry.get('path')}")
    return 0
