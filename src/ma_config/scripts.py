"""
Compatibility wrapper: delegates to shared.config.scripts (source of truth).
"""
from shared.config.scripts import (
    DEFAULT_REPO_ENV,
    DEFAULT_PYTHON,
    DEFAULT_LYRIC_LCI_PROFILE,
    DEFAULT_LYRIC_LCI_CALIBRATION,
)

__all__ = [
    "DEFAULT_REPO_ENV",
    "DEFAULT_PYTHON",
    "DEFAULT_LYRIC_LCI_PROFILE",
    "DEFAULT_LYRIC_LCI_CALIBRATION",
]
