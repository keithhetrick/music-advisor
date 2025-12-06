"""
Compatibility shim for plugins (relocated under engines/audio_engine/plugins).

Extends __path__ so imports like `plugins.logging.json_printer` continue to work.
"""
from __future__ import annotations

import pkgutil
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NEW_PLUGINS = _REPO_ROOT / "engines" / "audio_engine" / "plugins"

# Extend namespace to the new location
__path__ = pkgutil.extend_path(__path__, __name__)  # type: ignore[name-defined]
if _NEW_PLUGINS.exists():
    __path__.append(str(_NEW_PLUGINS))

__all__: list[str] = []
