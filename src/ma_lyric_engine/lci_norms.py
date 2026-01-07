"""Compatibility wrapper to relocated lyrics engine."""
from ma_lyrics_engine.lci_norms import (
    build_lane_norms,
    collect_records,
    mean_std,
    write_lane_norms,
)

__all__ = [
    "build_lane_norms",
    "collect_records",
    "mean_std",
    "write_lane_norms",
]
