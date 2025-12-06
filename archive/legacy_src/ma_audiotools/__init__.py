"""
Compatibility shim for the legacy ``ma_audiotools`` package.

The real code now lives in ``ma_audio_engine``; this module forwards imports so
older entry points (including ``music-advisor.always_present``) keep
working while downstream callers migrate.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Dict

_TARGET_PACKAGE = "ma_audio_engine"

# Map legacy submodules to their new homes inside ma_audio_engine.
_SUBMODULE_ALIASES: Dict[str, str] = {
    "always_present": "ma_audio_engine.always_present",
    "schemas": "ma_audio_engine.schemas",
    "policy": "ma_audio_engine.policy",
    "extract_cli": "ma_audio_engine.extract_cli",
    "pipe_cli": "ma_audio_engine.pipe_cli",
    "smoke": "ma_audio_engine.smoke",
    "engines": "ma_audio_engine.engines",
    "engines.axes": "ma_audio_engine.engines.axes",
    "host": "ma_audio_engine.host",
    "host.baseline_loader": "ma_audio_engine.host.baseline_loader",
    "host.baseline_normalizer": "ma_audio_engine.host.baseline_normalizer",
    "adapters": "ma_audio_engine.adapters",
}

_target_pkg: ModuleType = importlib.import_module(_TARGET_PACKAGE)
_warned = False


def __getattr__(name: str):
    # Delegate attribute lookups to the new package to stay API-compatible.
    return getattr(_target_pkg, name)


# Register submodule aliases so ``import ma_audiotools.always_present`` works.
for legacy_name, target_name in _SUBMODULE_ALIASES.items():
    try:
        module = importlib.import_module(target_name)
    except Exception:
        continue
    sys.modules[f"{__name__}.{legacy_name}"] = module

# Make ``from ma_audiotools import *`` behave like ma_audio_engine.
__all__ = getattr(_target_pkg, "__all__", [])

# Emit a deprecation warning once per import.
if not _warned:
    import warnings

    warnings.warn(
        "ma_audiotools is deprecated; import ma_audio_engine.* instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    _warned = True
