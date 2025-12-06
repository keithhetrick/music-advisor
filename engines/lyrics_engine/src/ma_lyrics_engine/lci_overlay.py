"""
Overlay LCI/TTC against lane norms.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional


def load_norms(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_lane(norms: Dict[str, object], tier: Optional[int], era_bucket: Optional[str], profile: Optional[str]) -> Optional[Dict[str, object]]:
    prof = profile or norms.get("profile")
    for lane in norms.get("lanes", []):
        if lane.get("tier") == tier and lane.get("era_bucket") == era_bucket:
            return lane
    return None


def zscore(val: Optional[float], mean: Optional[float], std: Optional[float]) -> Optional[float]:
    if val is None or mean is None or std is None:
        return None
    if std == 0:
        return 0.0
    return (val - mean) / std


def overlay_lci(
    song_axes: Dict[str, float],
    lci_score: Optional[float],
    ttc_seconds: Optional[float],
    lane_norms: Dict[str, object],
) -> Dict[str, object]:
    axes_z = {}
    for ax, val in song_axes.items():
        axes_z[ax] = zscore(val, lane_norms["axes_mean"].get(ax), lane_norms["axes_std"].get(ax))
    lci_score_z = zscore(lci_score, lane_norms.get("lci_score_mean"), lane_norms.get("lci_score_std"))
    ttc_z = zscore(ttc_seconds, lane_norms.get("ttc_seconds_mean"), lane_norms.get("ttc_seconds_std"))
    return {"axes_z": axes_z, "lci_score_z": lci_score_z, "ttc_seconds_z": ttc_z}
