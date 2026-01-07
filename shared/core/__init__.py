"""
Shared core contracts (shim layer).

Keep core-level helpers here so engines/hosts can import from `shared.core.*`.
Currently re-exports profile helpers from shared.config.
"""

from shared.core.profiles import (
    DEFAULT_LCI_PROFILE,
    DEFAULT_LCI_CALIBRATION_PATH,
    DEFAULT_TTC_PROFILE,
    DEFAULT_TTC_CONFIG_PATH,
    resolve_profile_config,
)

__all__ = [
    "DEFAULT_LCI_PROFILE",
    "DEFAULT_LCI_CALIBRATION_PATH",
    "DEFAULT_TTC_PROFILE",
    "DEFAULT_TTC_CONFIG_PATH",
    "resolve_profile_config",
]
