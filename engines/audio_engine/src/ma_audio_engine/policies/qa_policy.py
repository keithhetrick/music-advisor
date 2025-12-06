"""
QA policy: provides thresholds for clipping/silence/low-level depending on policy.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QAPolicy:
    clip_peak_threshold: float
    silence_ratio_threshold: float
    low_level_dbfs_threshold: float


POLICIES = {
    "default": QAPolicy(clip_peak_threshold=0.999, silence_ratio_threshold=0.9, low_level_dbfs_threshold=-40.0),
    # Slightly tighter silence threshold and low-level gate for strict.
    "strict": QAPolicy(clip_peak_threshold=0.999, silence_ratio_threshold=0.85, low_level_dbfs_threshold=-38.0),
    "lenient": QAPolicy(clip_peak_threshold=0.999, silence_ratio_threshold=0.95, low_level_dbfs_threshold=-45.0),
}


def get_policy(name: str) -> QAPolicy:
    return POLICIES.get(name, POLICIES["default"])
