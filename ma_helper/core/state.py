"""User preferences, history, and guard level helpers."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from .env import FAVORITES_PATH, LOG_FILE


def load_favorites(path: Path = FAVORITES_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"favorites": [], "history": [], "theme": {}, "last_failed": "", "last_base": "", "guard": "normal"}
    try:
        data = json.loads(path.read_text())
        if "guard" not in data:
            data["guard"] = "normal"
        return data
    except Exception:
        return {"favorites": [], "history": [], "theme": {}, "last_failed": "", "last_base": "", "guard": "normal"}


def save_favorites(data: Dict[str, Any], path: Path = FAVORITES_PATH) -> None:
    if os.environ.get("MA_HELPER_NO_WRITE") == "1":
        return
    try:
        path.write_text(json.dumps(data, indent=2))
    except Exception as exc:
        print(f"[ma] warning: could not persist prefs ({exc})", file=sys.stderr)


def guard_level() -> str:
    return load_favorites().get("guard", "normal")


def set_guard_level(level: str) -> None:
    data = load_favorites()
    data["guard"] = level
    save_favorites(data)


def add_history(cmd: str) -> None:
    data = load_favorites()
    hist: List[str] = data.get("history", [])
    hist.append(cmd)
    data["history"] = hist[-50:]
    save_favorites(data)


def ensure_favorite(name: str, cmd: str) -> None:
    data = load_favorites()
    favs = data.get("favorites", [])
    favs = [f for f in favs if f.get("name") != name]
    favs.append({"name": name, "cmd": cmd})
    data["favorites"] = favs
    save_favorites(data)


def set_last_failed(cmd: str) -> None:
    data = load_favorites()
    data["last_failed"] = cmd
    save_favorites(data)


def set_last_base(base: str) -> None:
    data = load_favorites()
    data["last_base"] = base
    save_favorites(data)
