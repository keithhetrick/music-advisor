"""
Lane assignment helpers (tier + era buckets).
"""
from __future__ import annotations

from typing import Optional, Tuple

from ma_config.constants import ERA_BUCKETS, ERA_BUCKET_MISC, TIER_THRESHOLDS


def era_bucket(year: Optional[int]) -> Optional[str]:
    if not year:
        return None
    for start, end in ERA_BUCKETS:
        if start <= year <= end:
            return f"{start}_{end}"
    return ERA_BUCKET_MISC


def tier_from_rank(rank: Optional[int]) -> Optional[int]:
    if rank is None:
        return None
    for ceiling, tier in TIER_THRESHOLDS:
        if rank <= ceiling:
            return tier
    return None


def assign_lane(year: Optional[int], peak_position: Optional[int], source: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    tier = tier_from_rank(peak_position)
    era = era_bucket(year)
    if source == "wip_stt" and tier is None:
        # WIP: keep tier None, era from provided year (if any)
        return None, era
    return tier, era


def lane_key(tier: Optional[int], era_bucket: Optional[str]) -> Optional[str]:
    if tier is None or not era_bucket:
        return None
    return f"tier{tier}__{era_bucket}"

__all__ = [
    "assign_lane",
    "era_bucket",
    "lane_key",
    "tier_from_rank",
]
