"""
Core profile helpers (shim to shared.config.profiles).
"""
from shared.config.profiles import (
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
