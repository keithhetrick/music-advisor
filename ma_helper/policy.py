"""Least-privilege gate for ma_helper commands."""
from __future__ import annotations

import os
import sys
from typing import Callable


def permission_level(args) -> str:
    if getattr(args, "unlock_danger", False) or os.environ.get("MA_UNLOCK", "").lower() == "danger":
        return "danger"
    if getattr(args, "unlock_write", False) or os.environ.get("MA_UNLOCK", "").lower() == "write":
        return "write"
    return "safe"


def require_unlock(kind: str, args, *, require_confirm: Callable[[str], bool] | None = None) -> bool:
    """
    Enforce unlock flags for write/destructive actions.
    """
    level = permission_level(args)
    if kind == "write":
        if level in {"write", "danger"}:
            return True
        print("[ma] REFUSED: write requires --unlock-write or MA_UNLOCK=write", file=sys.stderr)
        return False
    if kind == "danger":
        if level != "danger":
            print("[ma] REFUSED: destructive action requires --unlock-danger or MA_UNLOCK=danger", file=sys.stderr)
            return False
        if require_confirm and not getattr(args, "yes", False):
            return require_confirm("Confirm destructive action?")
        return True
    return True
