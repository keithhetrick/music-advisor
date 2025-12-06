"""
Compatibility shim for relocated aee_ml (audio ML helpers).

Extends __path__ to engines/audio_engine/src/ma_audio_engine/aee_ml so
imports continue working during the migration.
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_AEE_PATH = _REPO_ROOT / "engines" / "audio_engine" / "src" / "ma_audio_engine" / "aee_ml"

if _AEE_PATH.exists():
    __path__.append(str(_AEE_PATH))

try:
    _mod = import_module("ma_audio_engine.aee_ml")
    for name in getattr(_mod, "__all__", []):
        globals()[name] = getattr(_mod, name)
except Exception:
    pass

__all__ = getattr(_mod, "__all__", []) if " _mod" in locals() else []
