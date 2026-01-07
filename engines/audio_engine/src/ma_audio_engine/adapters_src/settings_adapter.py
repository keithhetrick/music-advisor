"""
Settings adapter: central place to parse runtime settings from env/args (logging, cache, tempo confidence, QA policy).

Purpose:
- Keep CLI code light by centralizing repeated env parsing (LOG_* controls) and optional config/settings.json defaults.
- Provide a single struct for runtime settings that downstream tools can reuse.

Sources and precedence:
- LOG_* env vars (LOG_JSON, LOG_REDACT, LOG_REDACT_VALUES, LOG_SANDBOX) seed logging defaults.
- config/settings.json (optional) can set cache_dir, tempo_conf_lower/upper, qa_policy, and logging defaults.
- CLI args (if present) override config for cache_dir/tempo_conf/qa_policy and can turn on logging flags.

Usage:
- `log_settings = load_log_settings(args)` to honor env + CLI.
- `settings = load_runtime_settings(args)` to combine config + env + CLI into a RuntimeSettings dataclass.

Notes:
- Side effects: none (reads env/files only).
- Validation: parsing is permissive; bad config/settings.json is swallowed to keep CLIs running with defaults.
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

__all__ = [
    "LogSettings",
    "RuntimeSettings",
    "load_log_settings",
    "load_runtime_settings",
]

_SETTINGS_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.json"


@dataclass
class LogSettings:
    log_json: bool
    log_redact: bool
    log_redact_values: List[str]
    log_sandbox: bool


@dataclass
class RuntimeSettings:
    log: LogSettings
    cache_dir: Optional[str] = None
    tempo_conf_lower: Optional[float] = None
    tempo_conf_upper: Optional[float] = None
    qa_policy: Optional[str] = None


def load_log_settings(args: Optional[object] = None) -> LogSettings:
    """
    Combine env + argparse overrides for logging controls.
    Recognizes: LOG_JSON, LOG_REDACT, LOG_REDACT_VALUES, LOG_SANDBOX and
    optional argparse attributes: log_json, log_redact, log_redact_values, log_sandbox.
    """
    env = os.environ
    log_json = env.get("LOG_JSON", "0") == "1"
    log_redact = env.get("LOG_REDACT", "0") == "1"
    log_redact_values = [v for v in env.get("LOG_REDACT_VALUES", "").split(",") if v]
    log_sandbox = env.get("LOG_SANDBOX", "0") == "1"

    if args is not None:
        if hasattr(args, "log_json"):
            log_json = log_json or bool(getattr(args, "log_json"))
        if hasattr(args, "log_redact"):
            log_redact = bool(getattr(args, "log_redact")) or log_redact
        if hasattr(args, "log_redact_values") and getattr(args, "log_redact_values"):
            log_redact_values = [v for v in str(getattr(args, "log_redact_values")).split(",") if v]
        if hasattr(args, "log_sandbox"):
            log_sandbox = bool(getattr(args, "log_sandbox")) or log_sandbox

    return LogSettings(
        log_json=log_json,
        log_redact=log_redact,
        log_redact_values=log_redact_values,
        log_sandbox=log_sandbox,
    )


def load_runtime_settings(args: Optional[object] = None, config_path: Optional[Path] = None) -> RuntimeSettings:
    """
    Load shared runtime settings from config/settings.json (if present) + env + optional argparse args.
    CLI args take precedence over config; env takes precedence over config for LOG_*.
    """
    cfg_path = config_path or _SETTINGS_PATH
    cfg: dict = {}
    try:
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
    except Exception:
        cfg = {}

    log = load_log_settings(args)

    cache_dir = cfg.get("cache_dir")
    tempo_conf_lower = cfg.get("tempo_conf_lower")
    tempo_conf_upper = cfg.get("tempo_conf_upper")
    qa_policy = cfg.get("qa_policy")

    if args is not None:
        if hasattr(args, "cache_dir") and getattr(args, "cache_dir"):
            cache_dir = getattr(args, "cache_dir")
        if hasattr(args, "tempo_sidecar_conf_lower") and getattr(args, "tempo_sidecar_conf_lower") is not None:
            tempo_conf_lower = getattr(args, "tempo_sidecar_conf_lower")
        if hasattr(args, "tempo_sidecar_conf_upper") and getattr(args, "tempo_sidecar_conf_upper") is not None:
            tempo_conf_upper = getattr(args, "tempo_sidecar_conf_upper")
        if hasattr(args, "qa_policy") and getattr(args, "qa_policy"):
            qa_policy = getattr(args, "qa_policy")

    return RuntimeSettings(
        log=log,
        cache_dir=cache_dir,
        tempo_conf_lower=float(tempo_conf_lower) if tempo_conf_lower is not None else None,
        tempo_conf_upper=float(tempo_conf_upper) if tempo_conf_upper is not None else None,
        qa_policy=qa_policy,
    )
