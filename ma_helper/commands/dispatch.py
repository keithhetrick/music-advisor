"""Thin dispatcher helpers shared by the CLI entrypoint."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import time

from ma_helper.core.state import guard_level
from ma_helper.core.git import git_summary


def log_event(load_favorites: Callable[[], dict], log_file: Path | None, entry: dict[str, Any], root: Path | None = None) -> None:
    """Append a structured log entry if logging is enabled."""
    try:
        cfg = load_favorites()
        if cfg.get("logging_disabled") or log_file is None:
            return
        payload = dict(entry)
        payload.setdefault("ts", time.time())
        if root is not None:
            payload.setdefault("root", str(root))
        payload.setdefault("git", git_summary())
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(__import__("json").dumps(payload) + "\n")
    except Exception:
        # Best-effort logging; never break the CLI.
        return


def require_confirm(prompt: str) -> bool:
    """Prompt for confirmation when guard is strict or MA_REQUIRE_CONFIRM=1."""
    if guard_level() != "strict" and os.environ.get("MA_REQUIRE_CONFIRM") != "1":
        return True
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
        return ans in ("y", "yes")
    except Exception:
        return False


def run_cmd(
    cmd: str,
    *,
    cwd: Path | None,
    dry_run: bool,
    orch_root: Path,
    log_event_fn: Callable[[dict[str, Any]], None] | None,
    set_last_failed: Callable[[str], None] | None,
    status_update: Callable[[], None] | None = None,
) -> int:
    """Execute a shell command with optional dry-run and logging."""
    print(f"[ma] {cmd}" + (" [dry-run]" if dry_run else ""))
    if dry_run:
        return 0
    start = time.time()
    if status_update:
        try:
            status_update()
        except Exception:
            pass
    rc = subprocess.call(cmd, shell=True, cwd=cwd or orch_root)
    if log_event_fn:
        try:
            log_event_fn({"cmd": cmd, "rc": rc, "duration_sec": round(time.time() - start, 3)})
        except Exception:
            pass
    if status_update:
        try:
            status_update()
        except Exception:
            pass
    if rc != 0 and set_last_failed:
        set_last_failed(cmd)
    return rc
