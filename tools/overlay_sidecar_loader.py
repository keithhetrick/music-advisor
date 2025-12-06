"""
Host/chat-friendly helpers to load tempo/key sidecars and return humanized payloads
without recomputing stats. This keeps recommendation/UI layers thin and modular.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _safe_read(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _label_lane_profile(shape: Dict[str, Any]) -> str:
    try:
        flatness = float(shape.get("flatness", 0.0))
        skew = float(shape.get("skew", 0.0))
    except Exception:
        return ""
    if flatness < 0.7:
        return "peaked_lane"
    if flatness > 0.9:
        return "flat_lane"
    if abs(skew) > 0.5:
        return "skewed_lane"
    return "balanced_lane"

def _validate_sidecar_fields(payload: Dict[str, Any], kind: str) -> Optional[str]:
    if not isinstance(payload, dict):
        return f"{kind}_sidecar_invalid"
    required = {
        "tempo": ["lane_id", "song_bpm", "lane_stats", "advisory_text"],
        "key": ["lane_id", "song_key", "lane_stats", "advisory"],
    }.get(kind, [])
    missing = [f for f in required if f not in payload]
    if missing:
        return f"{kind}_sidecar_missing:{','.join(missing)}"
    return None


def load_tempo_overlay_payload(
    client_rich_path: Path,
    sidecar_path: Optional[Path] = None,
    top_neighbor_bins: Optional[int] = 2,
) -> Optional[Dict[str, Any]]:
    """
    Given a .client.rich.txt path, load the sibling tempo_norms sidecar and
    return a small dict tailored for chat/reco surfaces.
    """
    client_rich_path = client_rich_path.expanduser().resolve()
    if sidecar_path:
        sidecar = sidecar_path.expanduser().resolve()
    else:
        base = client_rich_path.parent
        stem = client_rich_path.name.replace(".client.rich.txt", "")
        sidecar = base / f"{stem}.tempo_norms.json"
    payload = _safe_read(sidecar)
    if not payload:
        return None
    warn = _validate_sidecar_fields(payload, "tempo")
    lane_stats = payload.get("lane_stats") or {}
    peak_clusters = lane_stats.get("peak_clusters") or []
    primary_peak = peak_clusters[0] if peak_clusters else None
    shape = lane_stats.get("shape") or {}
    neighbor_bins = payload.get("neighbor_bins") or []
    if isinstance(top_neighbor_bins, int) and top_neighbor_bins > 0:
        neighbor_bins = neighbor_bins[:top_neighbor_bins]
    return {
        "lane_id": payload.get("lane_id"),
        "song_bpm": payload.get("song_bpm"),
        "hot_zone": lane_stats.get("peak_cluster_bpm_range"),
        "hit_medium_percentile_band": lane_stats.get("hit_medium_percentile_band"),
        "primary_peak": primary_peak,
        "shape": shape,
        "lane_profile": _label_lane_profile(shape),
        "neighbor_bins": neighbor_bins,
        "warning": warn,
        "advisory": {
            "label": payload.get("advisory_label"),
            "text": payload.get("advisory_text"),
            "suggested_bpm_range": payload.get("suggested_bpm_range"),
            "suggested_delta_bpm": payload.get("suggested_delta_bpm"),
        },
    }


def load_key_overlay_payload(
    client_rich_path: Path,
    sidecar_path: Optional[Path] = None,
    top_target_moves: Optional[int] = 3,
) -> Optional[Dict[str, Any]]:
    """
    Given a .client.rich.txt path, load the sibling key_norms sidecar and
    return a small dict tailored for chat/reco surfaces.
    """
    client_rich_path = client_rich_path.expanduser().resolve()
    if sidecar_path:
        sidecar = sidecar_path.expanduser().resolve()
    else:
        base = client_rich_path.parent
        stem = client_rich_path.name.replace(".client.rich.txt", "")
        sidecar = base / f"{stem}.key_norms.json"
    payload = _safe_read(sidecar)
    if not payload:
        return None
    warn = _validate_sidecar_fields(payload, "key")
    lane_stats = payload.get("lane_stats") or {}
    advisory = payload.get("advisory") or {}
    target_moves = advisory.get("target_key_moves") or []
    if isinstance(top_target_moves, int) and top_target_moves > 0:
        target_moves = target_moves[:top_target_moves]
    return {
        "lane_id": payload.get("lane_id"),
        "song_key": payload.get("song_key"),
        "lane_shape": lane_stats.get("lane_shape"),
        "mode_top_keys": lane_stats.get("mode_top_keys"),
        "fifths_chain": lane_stats.get("fifths_chain"),
        "historical_hit_medium": lane_stats.get("historical_hit_medium"),
        "neighbor_keys": (payload.get("song_placement") or {}).get("neighbor_keys") or [],
        "target_key_moves": target_moves,
        "warning": warn,
        "advisory": {
            "label": advisory.get("advisory_label"),
            "text": advisory.get("advisory_text"),
            "suggested_key_family": advisory.get("suggested_key_family"),
            "suggested_transpositions": advisory.get("suggested_transpositions"),
        },
    }


__all__ = ["load_tempo_overlay_payload", "load_key_overlay_payload"]
