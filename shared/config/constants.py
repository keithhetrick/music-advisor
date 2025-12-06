"""
Shared constants for lanes, tiers, and axes.

Usage:
- `ERA_BUCKETS`: tuples of (start_year, end_year) for era grouping; `ERA_BUCKET_MISC` for uncategorized.
- `TIER_THRESHOLDS`: ordered (threshold, tier_id) pairs; used to map scores/counts to tier buckets.
- `LCI_AXES`: canonical LCI axis names used across lyric/intel payloads.

These values are referenced by ranking/echo/intel pipelines; keep them stable unless
updating downstream consumers and docs.
"""
from __future__ import annotations

ERA_BUCKETS = [
    (1985, 1994),
    (1995, 2004),
    (2005, 2014),
    (2015, 2024),
]
ERA_BUCKET_MISC = "misc"

# (threshold, tier_id) ordered ascending by threshold ceiling.
TIER_THRESHOLDS = [
    (40, 1),
    (100, 2),
    (200, 3),
]

LCI_AXES = [
    "structure_fit",
    "prosody_ttc_fit",
    "rhyme_texture_fit",
    "diction_style_fit",
    "pov_fit",
    "theme_fit",
]
