"""
Helper to consolidate bridge + neighbors into a Lyric WIP bundle for host consumption.
"""
from __future__ import annotations

import math
from typing import Dict, Any, Optional


def to_percentile(z: Optional[float]) -> Optional[float]:
    if z is None:
        return None
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def build_bundle(bridge: Dict[str, Any], neighbors: Dict[str, Any]) -> Dict[str, Any]:
    items = bridge.get("items") or []
    if not items:
        return {}
    song = items[0]
    lci = song.get("lyric_confidence_index") or {}
    overlay = lci.get("overlay") or {}
    axes = lci.get("axes") or {}
    percentiles = {}
    axes_z = overlay.get("axes_z") or {}
    for ax, z in axes_z.items():
        percentiles[ax] = to_percentile(z)
    overall_p = to_percentile(overlay.get("lci_score_z"))
    bundle = {
        "song_id": song.get("song_id"),
        "title": song.get("title"),
        "artist": song.get("artist"),
        "year": song.get("year"),
        "lane": {"tier": song.get("tier"), "era_bucket": song.get("era_bucket")},
        "lci": {
            "score": lci.get("score"),
            "raw": lci.get("raw"),
            "calibration_profile": lci.get("calibration_profile"),
            "axes": axes,
            "percentiles": {"overall": overall_p, **percentiles},
        },
        "ttc": song.get("ttc_profile") or {},
        "neighbors": neighbors.get("items") or [],
    }
    return bundle

__all__ = [
    "build_bundle",
    "to_percentile",
]
