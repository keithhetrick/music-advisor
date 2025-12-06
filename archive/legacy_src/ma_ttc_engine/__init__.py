"""
Compatibility shim for relocated TTC engine (ma_ttc_engine).

Extends __path__ to engines/ttc_engine/src so imports resolve without
changing downstream code immediately.
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENGINE_TTC = _REPO_ROOT / "engines" / "ttc_engine" / "src" / "ma_ttc_engine"

if _ENGINE_TTC.exists():
    __path__.append(str(_ENGINE_TTC))

# Re-export primary submodules for convenience
try:
    ttc_features = import_module("ma_ttc_engine.ttc_features")
    detect_choruses = import_module("ma_ttc_engine.detect_choruses")
    __all__ = []
    if hasattr(ttc_features, "__all__"):
        __all__.extend(ttc_features.__all__)
    if hasattr(detect_choruses, "__all__"):
        __all__.extend(detect_choruses.__all__)
    globals().update({k: getattr(ttc_features, k) for k in dir(ttc_features) if not k.startswith("_")})
    globals().update({k: getattr(detect_choruses, k) for k in dir(detect_choruses) if not k.startswith("_")})
except Exception:
    __all__ = []
