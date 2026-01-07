"""
Backend registry adapter: surfaces supported tempo sidecar backends and the
default sidecar command. Keeps sidecar wiring modular and easy to extend.

Config:
- file: config/backend_registry.json controls enabled backends, default sidecar cmd,
  and per-backend sidecar commands/settings.
- env: none (callers pass backend explicitly or rely on config defaults).

Usage:
- `list_supported_backends()` → available names (from config or defaults)
- `get_default_sidecar_cmd()` or `get_sidecar_cmd_for_backend("essentia")`
- `is_backend_enabled("madmom")` to gate optional flows

Notes:
- Side effects: none (pure helpers).
- Unknown/disabled backends fall back to defaults to keep callers resilient.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from ma_audio_engine.adapters_src import plugin_loader

__all__ = [
    "list_supported_backends",
    "get_default_sidecar_cmd",
    "get_sidecar_cmd_for_backend",
    "is_backend_enabled",
    "get_backend_settings",
    "validate_sidecar_cmd",
]

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "backend_registry.json"
# Keep the default inline here to avoid import cycles with sidecar_adapter.
_DEFAULT_SIDECAR_CMD = "python3 tools/tempo_sidecar_runner.py --audio {audio} --out {out}"


def _load_cfg() -> Dict[str, Any]:
    try:
        if _CFG_PATH.exists():
            data = json.loads(_CFG_PATH.read_text())
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def list_supported_backends() -> List[str]:
    data = _load_cfg()
    backends = data.get("supported_backends")
    if isinstance(backends, list) and backends:
        return [str(b) for b in backends]
    return ["essentia", "madmom", "librosa", "auto"]


def get_default_sidecar_cmd() -> str:
    data = _load_cfg()
    cmd = data.get("default_sidecar_cmd")
    if isinstance(cmd, str) and cmd.strip():
        return cmd
    return _DEFAULT_SIDECAR_CMD


def get_sidecar_cmd_for_backend(name: Optional[str]) -> str:
    """
    Return a backend-specific sidecar cmd if configured and enabled,
    otherwise fall back to the global default.
    """
    data = _load_cfg()
    if name:
        backends = data.get("backends")
        if isinstance(backends, dict):
            backend_cfg = backends.get(name, {}) or {}
            if isinstance(backend_cfg, dict):
                cmd = backend_cfg.get("sidecar_cmd")
                if isinstance(cmd, str) and cmd.strip() and is_backend_enabled(name):
                    return cmd
    return get_default_sidecar_cmd()


def is_backend_enabled(name: str) -> bool:
    data = _load_cfg()
    enabled = data.get("enabled_backends")
    if isinstance(enabled, dict):
        flag = enabled.get(name)
        if flag is not None:
            return bool(flag)
    return True


def get_backend_settings(name: str) -> Dict[str, Any]:
    data = _load_cfg()
    settings = data.get("backends")
    if isinstance(settings, dict):
        cfg = settings.get(name)
        if isinstance(cfg, dict):
            return cfg
    return {}


def validate_sidecar_cmd(cmd: str) -> bool:
    """
    Optional plug-in hook to validate custom sidecar commands.
    If a validator plugin exists (plugins/sidecar_validators/default_validator.py
    with a callable `validate(cmd)`), defer to it; otherwise accept.
    """
    factory = plugin_loader.load_factory("sidecar_validators", "default_validator", factory_attr="validate")
    if factory:
        try:
            return bool(factory(cmd))
        except Exception:
            return False
    return True
