"""Python/venv resolution helpers for ma_helper."""
from __future__ import annotations

import sys
from pathlib import Path

from ma_helper.core import env


def resolve_python() -> Path:
    """
    Prefer repo-local .venv/bin/python; fall back to current interpreter.
    """
    candidate = env.ROOT / ".venv" / "bin" / "python"
    if candidate.exists():
        return candidate
    return Path(sys.executable)
