"""
Lightweight plugin loader scaffold to keep adapters swappable.
Currently unused by the pipeline, but available for future drop-in backends
or emitters (tempo sidecars, QA policies, logging sinks, exporters).

Usage:
- `list_plugins("logging")` → discover modules under plugins/logging/.
- `load_plugin(kind, name)` → import plugins.<kind>.<name>.
- `load_factory(kind, name, factory_attr="factory")` → get a callable (respects config/plugins.json overrides).
- `load_from_config(kind, name, config_path=...)` → honor custom module paths from config.

Config:
- config/plugins.json may map kinds/names to module paths (e.g., {"logging": {"http": "my_pkg.http_logger"}}).
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import json

from shared.config.paths import get_repo_root

_PLUGINS_ROOT = get_repo_root() / "engines" / "audio_engine" / "plugins"
_DEFAULT_CONFIG = get_repo_root() / "config" / "plugins.json"


def list_plugins(kind: str) -> Dict[str, str]:
    """
    List available plugin modules under plugins/<kind>.
    Returns {name: module_path}.
    """
    root = _PLUGINS_ROOT / kind
    found: Dict[str, str] = {}
    if not root.is_dir():
        return found
    for mod in pkgutil.iter_modules([str(root)]):
        found[mod.name] = f"plugins.{kind}.{mod.name}"
    return found


def load_plugin(kind: str, name: str) -> Optional[Any]:
    """
    Import a plugin module by kind/name. Returns the module or None.
    """
    try:
        return importlib.import_module(f"plugins.{kind}.{name}")
    except Exception:
        return None


def load_from_config(kind: str, name: str, config_path: Path = _DEFAULT_CONFIG) -> Optional[Any]:
    """
    Load a plugin using config/plugins.json mapping: {kind: {name: module_path}}.
    Falls back to standard plugins.<kind>.<name> if not configured.
    """
    module_path = None
    try:
        if config_path.exists():
            cfg = json.loads(config_path.read_text())
            module_path = (cfg.get(kind) or {}).get(name)
    except Exception:
        module_path = None
    if not module_path:
        module_path = f"plugins.{kind}.{name}"
    try:
        return importlib.import_module(module_path)
    except Exception:
        return None


def load_factory(kind: str, name: str, factory_attr: str = "factory", config_path: Path = _DEFAULT_CONFIG) -> Optional[Callable]:
    """
    Load a plugin module (optionally via config/plugins.json) and return a callable attribute (default: factory).
    Returns None if missing or import fails.
    """
    module = load_from_config(kind, name, config_path=config_path)
    if module and hasattr(module, factory_attr):
        attr = getattr(module, factory_attr)
        if callable(attr):
            return attr
    return None
