"""
Compatibility wrapper: delegates to shared.config.pipeline (source of truth).
"""
from shared.config.pipeline import (
    HCI_BUILDER_PROFILE_DEFAULT,
    NEIGHBORS_PROFILE_DEFAULT,
    SIDECAR_TIMEOUT_DEFAULT,
)

__all__ = [
    "HCI_BUILDER_PROFILE_DEFAULT",
    "NEIGHBORS_PROFILE_DEFAULT",
    "SIDECAR_TIMEOUT_DEFAULT",
]
