from __future__ import annotations

from typing import Any, Dict, Optional


class NormsError(Exception):
    pass


def validate_norms_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    required = ["region", "tier", "version"]
    for k in required:
        if k not in snapshot:
            raise NormsError(f"market_norms_snapshot missing required field: {k}")
    return snapshot


def label_percentile(value: Optional[float], stats: Dict[str, Any]) -> str:
    """
    Given a value and a stats dict with p10/p25/p50/p75/p90, return a qualitative label.
    """
    if value is None:
        return "unknown"
    p10 = stats.get("p10")
    p25 = stats.get("p25")
    p50 = stats.get("p50")
    p75 = stats.get("p75")
    p90 = stats.get("p90")
    try:
        val = float(value)
    except Exception:
        return "unknown"
    if p10 is None or p25 is None or p50 is None or p75 is None or p90 is None:
        return "unknown"
    if val < p10:
        return "below_p10"
    if val < p25:
        return "between_p10_p25"
    if val < p50:
        return "between_p25_p50"
    if val < p75:
        return "between_p50_p75"
    if val < p90:
        return "between_p75_p90"
    return "above_p90"


def percentiles_for_feature(snapshot: Dict[str, Any], feature_key: str) -> Dict[str, Any]:
    stats = snapshot.get(feature_key) or {}
    return stats
