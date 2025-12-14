"""Repository root discovery and overrides."""
from __future__ import annotations

import os
from pathlib import Path


def discover_root(start: Path) -> Path:
    """Discover repo root by walking up to find .git; fallback to start."""
    env_root = os.environ.get("MA_HELPER_ROOT")
    if env_root:
        return Path(env_root).resolve()
    current = start.resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    return current
