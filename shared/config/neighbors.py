"""
Neighbor search defaults and helpers.

Defaults:
- limit: 5
- distance: cosine
- config: config/lyric_neighbors_default.json (if present)

Env overrides:
- LYRIC_NEIGHBORS_LIMIT, LYRIC_NEIGHBORS_DISTANCE, LYRIC_NEIGHBORS_CONFIG

Usage:
- `resolve_neighbors_config(cli_limit, cli_distance, cli_config)` → (limit, distance) with precedence CLI > env > config > defaults.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple, Optional, Dict

DEFAULT_NEIGHBORS_LIMIT = 5
DEFAULT_NEIGHBORS_DISTANCE = "cosine"
DEFAULT_NEIGHBORS_CONFIG_PATH = Path("config/lyric_neighbors_default.json")


def _load_json(path: Path) -> Optional[Dict[str, object]]:
    """Load JSON if present; swallow errors to keep resolution forgiving."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def resolve_neighbors_config(
    cli_limit: int | None,
    cli_distance: str | None,
    cli_config: str | None = None,
) -> Tuple[int, str]:
    """
    Resolve neighbors limit + distance with precedence:
    CLI > env > config JSON > defaults.
    Env vars: LYRIC_NEIGHBORS_LIMIT, LYRIC_NEIGHBORS_DISTANCE, LYRIC_NEIGHBORS_CONFIG.
    """
    env_limit = os.getenv("LYRIC_NEIGHBORS_LIMIT")
    env_distance = os.getenv("LYRIC_NEIGHBORS_DISTANCE")
    env_config = os.getenv("LYRIC_NEIGHBORS_CONFIG")
    config_path = (
        Path(cli_config).expanduser()
        if cli_config
        else (Path(env_config).expanduser() if env_config else DEFAULT_NEIGHBORS_CONFIG_PATH)
    )
    cfg = _load_json(config_path) if config_path.exists() else None
    cfg_limit = cfg.get("limit") if isinstance(cfg, dict) else None
    cfg_distance = cfg.get("distance") if isinstance(cfg, dict) else None

    limit = (
        cli_limit
        if cli_limit is not None
        else int(env_limit)
        if env_limit
        else int(cfg_limit)
        if cfg_limit is not None
        else DEFAULT_NEIGHBORS_LIMIT
    )
    distance = (
        cli_distance
        or env_distance
        or (cfg_distance if isinstance(cfg_distance, str) else None)
        or DEFAULT_NEIGHBORS_DISTANCE
    )
    return limit, distance
