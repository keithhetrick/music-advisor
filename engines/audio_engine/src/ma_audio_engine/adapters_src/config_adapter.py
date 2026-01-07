"""
Lightweight config overlay helpers to keep env/CLI/default precedence consistent.

Usage patterns:
- Resolve with precedence: `resolve_config_value(cli_val, env_var="MY_FLAG", default="x")`.
- Merge small override dicts: `overlay_config(base_cfg, overrides)` without mutating inputs.
- Build stable fingerprint components: `build_config_components(profile=..., cache_backend=...)` (drops None).

Notes:
- Side effects: none; pure helpers for precedence and fingerprint building.
- Coercion: pass a `coerce` callable to normalize env/CLI strings to the desired type.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

__all__ = [
    "resolve_config_value",
    "overlay_config",
    "build_config_components",
]


def resolve_config_value(
    cli_value: Any,
    env_var: Optional[str] = None,
    default: Any = None,
    coerce: Optional[Callable[[Any], Any]] = None,
) -> Any:
    """
    Resolve a config value with precedence:
      1) explicit CLI value (if not None)
      2) environment variable (if provided and set)
      3) fallback default
    Optionally coerce the value (e.g., int/float/bool parsing).
    """
    if cli_value is not None:
        return coerce(cli_value) if coerce else cli_value
    if env_var:
        env_val = os.getenv(env_var, None)
        if env_val is not None:
            return coerce(env_val) if coerce else env_val
    return default


def overlay_config(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shallow-merge overrides into base and return a new dict.
    Does not mutate inputs.
    """
    merged = dict(base or {})
    for k, v in (overrides or {}).items():
        if v is not None:
            merged[k] = v
    return merged


def build_config_components(**kwargs: Any) -> Dict[str, Any]:
    """
    Normalize config components for fingerprinting.

    - Drops None values so fingerprints remain stable.
    - Preserves insertion order supplied by the caller for deterministic JSON dumps.
    - Leaves values untouched so callers can pass ints/floats/strings/booleans directly.
    """
    return {k: v for k, v in kwargs.items() if v is not None}
