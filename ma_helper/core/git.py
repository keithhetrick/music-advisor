"""Lightweight git helpers used across commands."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict

from .env import CACHE_DIR, CACHE_FILE, FAVORITES_PATH, LAST_RESULTS_FILE, LOG_DIR, ROOT, STATE_HOME


def enforce_permissions(path: Path) -> bool:
    """Warn (but do not abort) if key helper files are not writable."""
    targets = [FAVORITES_PATH, CACHE_DIR, CACHE_FILE, LAST_RESULTS_FILE, LOG_DIR or STATE_HOME]
    ok = True
    for t in targets:
        parent = t if t.suffix else t
        try:
            parent.parent.mkdir(parents=True, exist_ok=True)
            test = parent if parent.suffix else parent / ".touch"
            test.touch(exist_ok=True)
        except Exception:
            ok = False
            print(f"[ma] warning: cannot write to {t}; some features (cache/logs/prefs) may be disabled.")
    return ok


def enforce_clean_tree() -> bool:
    """If MA_REQUIRE_CLEAN=1, ensure git working tree is clean."""
    if os.environ.get("MA_REQUIRE_CLEAN") != "1":
        return True
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        print("[ma] warning: MA_REQUIRE_CLEAN=1 but git/.git not available; skipping clean check.", file=sys.stderr)
        return True
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
        if res.stdout.strip():
            print("[ma] git working tree is dirty (MA_REQUIRE_CLEAN=1). Commit or stash, or unset MA_REQUIRE_CLEAN.", file=sys.stderr)
            return False
    except Exception:
        print("[ma] warning: unable to check git status; proceeding.", file=sys.stderr)
    return True


def _ahead_behind() -> tuple[str, str, str]:
    """Return (behind, ahead, upstream) vs tracking ref; returns '?' and 'none' if unknown."""
    upstream = "none"
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        upstream = res.stdout.strip()
        res = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        parts = res.stdout.strip().split()
        if len(parts) >= 2:
            behind, ahead = parts[0], parts[1]
            return behind, ahead, upstream
    except Exception:
        pass
    # Fallback: try origin/main if upstream missing
    try:
        res = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "origin/main...HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        parts = res.stdout.strip().split()
        if len(parts) >= 2:
            behind, ahead = parts[0], parts[1]
            return behind, ahead, "origin/main (fallback)"
    except Exception:
        pass
    return "?", "?", upstream


def git_summary() -> Dict[str, str]:
    summary = {"branch": "unknown", "dirty": "?", "ahead": "?", "behind": "?", "upstream": "none"}
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        return summary
    try:
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        summary["branch"] = res.stdout.strip()
    except Exception:
        pass
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
        summary["dirty"] = "dirty" if res.stdout.strip() else "clean"
    except Exception:
        pass
    behind, ahead, upstream = _ahead_behind()
    summary["behind"], summary["ahead"], summary["upstream"] = behind, ahead, upstream
    return summary
