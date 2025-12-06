"""
Shim for legacy imports; forwards to ma_audio_engine.always_present.
"""
from __future__ import annotations

import warnings
from ma_audio_engine.always_present import coerce_payload_shape

warnings.warn(
    "Root-level always_present.py is deprecated; import ma_audio_engine.always_present instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["coerce_payload_shape"]
