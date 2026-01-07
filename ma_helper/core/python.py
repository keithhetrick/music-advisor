"""Python/venv resolution helpers for ma_helper."""
from __future__ import annotations

import sys
from pathlib import Path

from ma_helper.core.config import RuntimeConfig


def resolve_python(runtime: RuntimeConfig | None = None) -> Path:
    """
    Prefer repo-local .venv/bin/python; fall back to current interpreter.
    """
    # Backward compatibility
    if runtime is None:
        from ma_helper.core import env
        root = env.ROOT
    else:
        root = runtime.root

    candidate = root / ".venv" / "bin" / "python"
    if candidate.exists():
        return candidate
    return Path(sys.executable)
