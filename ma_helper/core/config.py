"""Config loading for ma_helper (black-box ready)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import tomllib

DEFAULT_CONFIG_PATHS = [
    Path("ma_helper.toml"),
    Path(".ma_helper.toml"),
]


@dataclass
class HelperConfig:
    root: Path
    registry_path: Path
    task_aliases: Dict[str, str] = field(default_factory=dict)
    state_dir: Path | None = None
    log_file: Path | None = None
    telemetry_file: Path | None = None
    adapter: str = "ma_orchestrator"
    cache_dir: Path | None = None

    @classmethod
    def load(cls, root: Path, override_path: Optional[Path] = None) -> "HelperConfig":
        cfg_path = override_path
        if cfg_path is None:
            for candidate in DEFAULT_CONFIG_PATHS:
                if candidate.exists():
                    cfg_path = candidate
                    break
        data: Dict[str, Any] = {}
        if cfg_path and cfg_path.exists():
            with cfg_path.open("rb") as fh:
                data = tomllib.load(fh)
        adapter = os.environ.get("MA_HELPER_ADAPTER", data.get("adapter", "ma_orchestrator"))
        registry_path = Path(data.get("registry_path", "project_map.json"))
        aliases = data.get("tasks", {}) or {}
        state_dir = data.get("state_dir")
        log_file = data.get("log_file")
        telemetry_file = data.get("telemetry_file")
        cache_dir = data.get("cache_dir")

        # env overrides
        env_root = os.environ.get("MA_HELPER_ROOT")
        if env_root:
            root = Path(env_root).resolve()
        env_registry = os.environ.get("MA_HELPER_REGISTRY")
        if env_registry:
            registry_path = Path(env_registry)
        if os.environ.get("MA_HELPER_NO_WRITE") == "1":
            state_dir = None
            log_file = None
            telemetry_file = None
            cache_dir = None
        if state_dir:
            state_dir = Path(state_dir)
        if log_file:
            log_file = Path(log_file)
        if telemetry_file:
            telemetry_file = Path(telemetry_file)
        if cache_dir:
            cache_dir = Path(cache_dir)

        return cls(
            root=root,
            registry_path=registry_path if registry_path.is_absolute() else root / registry_path,
            task_aliases=aliases,
            state_dir=state_dir if state_dir is None or state_dir.is_absolute() else root / state_dir,
            log_file=log_file if log_file is None or log_file.is_absolute() else root / log_file,
            telemetry_file=telemetry_file if telemetry_file is None or telemetry_file.is_absolute() else root / telemetry_file,
            adapter=adapter,
            cache_dir=cache_dir if cache_dir is None or cache_dir.is_absolute() else root / cache_dir,
        )
