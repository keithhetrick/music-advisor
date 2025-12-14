"""Favorites/history/cache/logs helpers."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from ma_helper.core.cache import load_cache, save_cache
from ma_helper.core.env import ARTIFACT_DIR
from ma_helper.core.state import add_history, ensure_favorite, load_favorites


def handle_favorites(args) -> int:
    if args.fav_action == "list":
        return list_favorites(getattr(args, "json", False))
    if args.fav_action == "add":
        ensure_favorite(args.name, args.cmd)
        print(f"[ma] saved favorite '{args.name}' -> {args.cmd}")
        return 0
    if args.fav_action == "run":
        data = load_favorites()
        cmd_entry = next((f for f in data.get("favorites", []) if f.get("name") == args.name), None)
        if not cmd_entry:
            print(f"[ma] favorite '{args.name}' not found")
            return 1
        cmd = cmd_entry.get("cmd", "")
        if not cmd:
            print(f"[ma] favorite '{args.name}' has no command")
            return 1
        print(f"[ma] running favorite '{args.name}': {cmd}")
        add_history(cmd)
        import subprocess
        from ma_helper.core.env import ROOT
        return subprocess.call(cmd, shell=True, cwd=ROOT)
    return 1


def list_favorites(as_json: bool = False) -> int:
    data = load_favorites()
    favs = data.get("favorites", [])
    hist = data.get("history", [])
    theme = data.get("theme", {})
    last_base = data.get("last_base", "")
    last_failed = data.get("last_failed", "")
    if as_json:
        print(json.dumps({"favorites": favs, "history": hist, "theme": theme, "last_base": last_base, "last_failed": last_failed}, indent=2))
        return 0
    print("Favorites:")
    for fav in favs:
        print(f"- {fav.get('name')}: {fav.get('cmd')}")
    print("\nRecent history:")
    for h in hist[-10:]:
        print(f"- {h}")
    if theme:
        print("\nTheme:")
        for k, v in theme.items():
            print(f"- {k}: {v}")
    if last_base:
        print(f"\nLast base: {last_base}")
    if last_failed:
        print(f"Last failed command: {last_failed}")
    return 0


def handle_cache(args) -> int:
    action = args.action
    if action == "stats":
        cache = load_cache()
        print(json.dumps({"entries": len(cache)}, indent=2))
        return 0
    if action == "clean":
        save_cache({})
        print("[ma] cache cleared.")
        return 0
    if action == "list-artifacts":
        if not ARTIFACT_DIR.exists():
            print("[ma] no artifacts directory yet.")
            return 0
        for p in sorted(ARTIFACT_DIR.glob("*.json")):
            print(p.name)
        return 0
    if action == "show-artifact":
        name = args.name
        path = ARTIFACT_DIR / f"{name}.json"
        if not path.exists():
            print(f"[ma] artifact {name} not found")
            return 1
        print(path.read_text())
        return 0
    return 1


def handle_logs(args, log_file: Path | None) -> int:
    if log_file is None or not log_file.exists():
        print("[ma] no logs yet.")
        return 0
    tail = getattr(args, "tail", 50)
    lines = log_file.read_text().splitlines()[-tail:]
    for line in lines:
        print(line)
    return 0
