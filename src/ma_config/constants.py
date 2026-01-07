"""
Compatibility wrapper: delegates to shared.config.constants (source of truth).
"""
from shared.config.constants import (
    ERA_BUCKETS,
    ERA_BUCKET_MISC,
    TIER_THRESHOLDS,
    LCI_AXES,
)

__all__ = [
    "ERA_BUCKETS",
    "ERA_BUCKET_MISC",
    "TIER_THRESHOLDS",
    "LCI_AXES",
]
