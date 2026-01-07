"""
Core shared types and contracts (placeholder for future dataclasses).
Re-exports shared.core.* so callers can keep importing ma_core during migration.
"""
from shared.core import (
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
