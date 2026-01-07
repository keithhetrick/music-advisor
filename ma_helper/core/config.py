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


@dataclass(frozen=True)
class RuntimeConfig:
    """Immutable runtime configuration computed from HelperConfig and environment.

    This replaces the mutable globals in ma_helper.core.env with a frozen dataclass
    that is computed once and passed through the application.

    All paths are absolute and fully resolved. Environment variable overrides are
    applied during construction.
    """
    # Core paths
    root: Path
    state_home: Path

    # Cache paths
    cache_dir: Path
    cache_file: Path
    last_results_file: Path
    artifact_dir: Path

    # Log paths
    log_dir: Path
    log_file: Path | None
    telemetry_file: Path | None

    # User state
    favorites_path: Path

    # Flags
    cache_enabled: bool

    @classmethod
    def from_helper_config(cls, cfg: HelperConfig) -> "RuntimeConfig":
        """Create RuntimeConfig from HelperConfig, applying environment overrides.

        This method implements the same logic as env.apply_config() but creates
        an immutable object instead of mutating global variables.

        Environment variable precedence (highest to lowest):
        1. MA_HELPER_NO_WRITE=1 disables all caching/logging
        2. MA_LOG_FILE overrides log_file
        3. MA_TELEMETRY_FILE overrides telemetry_file
        4. MA_HELPER_HOME overrides default state_home
        5. HelperConfig fields (from ma_helper.toml)
        6. Defaults (ROOT/.ma_cache, ~/.ma_helper, etc.)

        Args:
            cfg: The HelperConfig loaded from ma_helper.toml and env vars

        Returns:
            Immutable RuntimeConfig with all paths resolved
        """
        # Compute state_home
        state_home = cfg.state_dir
        if state_home is None:
            ma_helper_home = os.environ.get("MA_HELPER_HOME", "")
            if ma_helper_home:
                state_home = Path(ma_helper_home)
            else:
                state_home = Path.home() / ".ma_helper"

        # Compute cache_dir and derived paths
        cache_dir = cfg.cache_dir
        if cache_dir is None:
            cache_dir = cfg.root / ".ma_cache"
        cache_file = cache_dir / "cache.json"
        last_results_file = cache_dir / "last_results.json"
        artifact_dir = cache_dir / "artifacts"

        # Compute log paths
        log_dir = state_home / "logs"
        log_file = cfg.log_file
        if log_file is None:
            log_file = log_dir / "ma.log"
        telemetry_file = cfg.telemetry_file
        if telemetry_file is None:
            telemetry_file = log_file

        # Environment variable overrides (highest precedence)
        if os.environ.get("MA_LOG_FILE"):
            log_file = Path(os.environ["MA_LOG_FILE"])
        if os.environ.get("MA_TELEMETRY_FILE"):
            telemetry_file = Path(os.environ["MA_TELEMETRY_FILE"])

        # Check cache enabled
        cache_enabled = os.environ.get("MA_HELPER_NO_WRITE") != "1"
        if not cache_enabled:
            log_file = None
            telemetry_file = None

        # Compute favorites path
        favorites_path = state_home / "config.json"

        return cls(
            root=cfg.root,
            state_home=state_home,
            cache_dir=cache_dir,
            cache_file=cache_file,
            last_results_file=last_results_file,
            artifact_dir=artifact_dir,
            log_dir=log_dir,
            log_file=log_file,
            telemetry_file=telemetry_file,
            favorites_path=favorites_path,
            cache_enabled=cache_enabled,
        )
