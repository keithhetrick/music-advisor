"""
Shared spine path helpers wrapping ma_config.paths.
"""
from __future__ import annotations

from pathlib import Path

from ma_config.paths import (
    get_spine_root,
    get_spine_backfill_root,
    get_spine_master_csv,
    get_repo_root,
    get_data_root,
)


def spine_root_override(root: str | Path | None) -> Path:
    return Path(root).expanduser() if root else get_spine_root()


def spine_backfill_root_override(root: str | Path | None) -> Path:
    return Path(root).expanduser() if root else get_spine_backfill_root()


def spine_master_override(path: str | Path | None) -> Path:
    return Path(path).expanduser() if path else get_spine_master_csv()


__all__ = [
    "get_spine_root",
    "get_spine_backfill_root",
    "get_spine_master_csv",
    "get_repo_root",
    "get_data_root",
    "spine_root_override",
    "spine_backfill_root_override",
    "spine_master_override",
]
