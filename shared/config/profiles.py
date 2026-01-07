"""
Profile resolution helpers shared across sidecars/hosts.

Precedence everywhere: CLI > env > JSON metadata > default.

Usage patterns:
- `resolve_profile_config(cli_profile, cli_config, env_profile_var, env_config_var, default_profile, default_config_path)`
  returns `(profile_name, config_path, config_json_or_none)` with consistent override rules and logging for missing/bad files.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from shared.config.paths import get_calibration_root

DEFAULT_LCI_PROFILE = "lci_us_pop_v1"
DEFAULT_LCI_CALIBRATION_PATH = get_calibration_root() / "lci_calibration_us_pop_v1.json"

DEFAULT_TTC_PROFILE = "ttc_us_pop_v1"
DEFAULT_TTC_CONFIG_PATH = get_calibration_root() / "ttc_profile_us_pop_v1.json"


def _maybe_path(val: Optional[str | Path]) -> Optional[Path]:
    """Return a Path if the input looks like a JSON path or exists; else None."""
    if val is None:
        return None
    p = Path(val).expanduser()
    if p.suffix.lower() == ".json" or p.exists():
        return p
    return None


def _load_json(path: Path, log) -> Optional[Dict[str, object]]:
    """Load JSON with warning logs on missing/parse errors (non-fatal)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log(f"[WARN] Profile config not found: {path}")
    except Exception as exc:  # pragma: no cover - defensive
        log(f"[WARN] Failed to parse profile config {path}: {exc}")
    return None


def resolve_profile_config(
    cli_profile: Optional[str],
    cli_config: Optional[str | Path],
    env_profile_var: str,
    env_config_var: str,
    default_profile: str,
    default_config_path: Path,
    log=print,
) -> Tuple[str, Path, Optional[Dict[str, object]]]:
    """
    Resolve a profile name and config JSON path with consistent precedence.

    Order:
    1) CLI profile name (if not a path) or CLI config path
    2) Env profile/config (if set)
    3) Default profile and config path

    Returns (profile_name, config_path, parsed_json_or_none). If the config is a
    JSON file and contains "calibration_profile" or "profile", those fields can
    update the profile name unless overridden by CLI/env. Logs warnings for
    missing/unparseable JSON but does not raise to keep callers resilient.
    """
    env_profile = os.getenv(env_profile_var)
    env_config = os.getenv(env_config_var)

    profile_is_path = cli_profile is not None and _maybe_path(cli_profile) is not None
    cli_profile_label = None if profile_is_path else cli_profile

    # Allow historical usage where --profile pointed at a JSON path.
    config_path = None
    if cli_config is not None:
        config_path = Path(cli_config).expanduser()
    elif profile_is_path:
        config_path = Path(cli_profile).expanduser()  # type: ignore[arg-type]
    elif env_config:
        config_path = Path(env_config).expanduser()
    if config_path is None:
        config_path = default_config_path
    config_path = Path(config_path).expanduser()

    profile = cli_profile_label or env_profile or default_profile
    config = _load_json(config_path, log) if config_path else None
    if config:
        profile = (
            cli_profile_label
            or env_profile
            or config.get("calibration_profile")
            or config.get("profile")
            or profile
        )
    return profile, config_path, config


__all__ = [
    "DEFAULT_LCI_PROFILE",
    "DEFAULT_LCI_CALIBRATION_PATH",
    "DEFAULT_TTC_PROFILE",
    "DEFAULT_TTC_CONFIG_PATH",
    "resolve_profile_config",
]
