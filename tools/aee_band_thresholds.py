# tools/aee_band_thresholds.py
"""
Band-threshold helper for MusicAdvisor AEE/HCI.

Purpose:
- Load axis thresholds (lo / hi cutoffs) from the JSON produced by
  tools/ma_band_thresholds_from_csv.py
- Provide small helpers to map a continuous feature value to a band:
    "lo" | "mid" | "hi"

Intended usage in the scoring pipeline:
    from tools.aee_band_thresholds import (
        get_band,
        get_energy_band,
        get_dance_band,
        load_thresholds,
    )

    energy_band = get_energy_band(features["energy"])
    dance_band  = get_dance_band(features["danceability"])
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

# Default location for the thresholds JSON
DEFAULT_THRESHOLDS_PATH = Path("calibration/aee_band_thresholds_v1_1.json")

# Fallback thresholds baked in from your 11/16/2025 calibration run
# (these are only used if the JSON cannot be loaded).
_FALLBACK_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "energy_feature": {
        "lo": 0.360707,
        "hi": 0.373529,
    },
    "danceability_feature": {
        "lo": 0.367329,
        "hi": 0.517685,
    },
}

# Simple aliases so callers can pass "energy" instead of "energy_feature", etc.
_AXIS_ALIASES: Dict[str, str] = {
    "energy": "energy_feature",
    "energy_feature": "energy_feature",
    "dance": "danceability_feature",
    "danceability": "danceability_feature",
    "dance_feature": "danceability_feature",
    "danceability_feature": "danceability_feature",
}

# Internal cache so we don't hit the filesystem repeatedly.
_THRESHOLDS_CACHE: Optional[Dict[str, Dict[str, float]]] = None


def _normalize_axis_name(axis_name: str) -> str:
    """Map various synonyms to the canonical axis key used in the JSON."""
    key = axis_name.strip().lower()
    if key not in _AXIS_ALIASES:
        raise KeyError(f"Unknown axis name '{axis_name}'. "
                       f"Expected one of: {sorted(_AXIS_ALIASES.keys())}")
    return _AXIS_ALIASES[key]


def load_thresholds(path: Path | str = DEFAULT_THRESHOLDS_PATH) -> Dict[str, Dict[str, float]]:
    """
    Load thresholds from JSON, with a baked-in fallback.

    JSON format (as produced by ma_band_thresholds_from_csv.py) is expected to be:
        {
          "energy_feature": {
            "lo": 0.360707,
            "hi": 0.373529,
            "p_lo": 0.3,
            "p_hi": 0.7,
            "count": 100
          },
          "danceability_feature": {
            "lo": 0.367329,
            "hi": 0.517685,
            "p_lo": 0.3,
            "p_hi": 0.7,
            "count": 100
          }
        }

    Returns a dict mapping axis_name -> {"lo": float, "hi": float}.
    """
    global _THRESHOLDS_CACHE

    if _THRESHOLDS_CACHE is not None:
        return _THRESHOLDS_CACHE

    path = Path(path)

    thresholds: Dict[str, Dict[str, float]] = {}

    if path.is_file():
        try:
            data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            for axis_key, axis_info in data.items():
                if not isinstance(axis_info, dict):
                    continue
                lo = axis_info.get("lo")
                hi = axis_info.get("hi")
                if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
                    thresholds[axis_key] = {"lo": float(lo), "hi": float(hi)}
        except Exception as e:
            # If there's an error, we fall back to baked-in thresholds.
            print(f"[WARN] Failed to load thresholds from {path}: {e!r}")
            thresholds = {}

    # Merge fallbacks for any missing axes
    for axis_key, fb in _FALLBACK_THRESHOLDS.items():
        thresholds.setdefault(axis_key, dict(fb))

    _THRESHOLDS_CACHE = thresholds
    return thresholds


def get_band(axis_name: str, value: float, thresholds: Optional[Dict[str, Dict[str, float]]] = None) -> str:
    """
    Map a continuous feature value to 'lo' | 'mid' | 'hi' for the given axis.

    axis_name:
        One of "energy_feature", "danceability_feature", or a known alias
        like "energy", "dance", "danceability".
    value:
        Continuous feature value (e.g. 0.368 for energy_feature).
    thresholds:
        Optional pre-loaded thresholds dict; if not provided, load_thresholds()
        will be called.

    Logic:
        if value < lo: return "lo"
        elif value > hi: return "hi"
        else: return "mid"
    """
    if thresholds is None:
        thresholds = load_thresholds()

    canonical = _normalize_axis_name(axis_name)

    if canonical not in thresholds:
        raise KeyError(
            f"No thresholds for axis '{canonical}'. "
            f"Available axes: {sorted(thresholds.keys())}"
        )

    lo = thresholds[canonical]["lo"]
    hi = thresholds[canonical]["hi"]

    v = float(value)
    if v < lo:
        return "lo"
    if v > hi:
        return "hi"
    return "mid"


def get_energy_band(value: float, thresholds: Optional[Dict[str, Dict[str, float]]] = None) -> str:
    """Convenience wrapper for energy_feature."""
    return get_band("energy_feature", value, thresholds=thresholds)


def get_dance_band(value: float, thresholds: Optional[Dict[str, Dict[str, float]]] = None) -> str:
    """Convenience wrapper for danceability_feature."""
    return get_band("danceability_feature", value, thresholds=thresholds)


if __name__ == "__main__":
    # Tiny CLI for quick manual checks, e.g.:
    #   python tools/aee_band_thresholds.py energy 0.37
    import argparse

    parser = argparse.ArgumentParser(description="Inspect band thresholds and compute bands.")
    parser.add_argument("axis", help="Axis name (e.g. energy, danceability)")
    parser.add_argument("value", type=float, help="Feature value (e.g. 0.368)")
    parser.add_argument(
        "--thresholds",
        type=str,
        default=str(DEFAULT_THRESHOLDS_PATH),
        help="Path to thresholds JSON (default: calibration/aee_band_thresholds_v1_1.json)",
    )

    args = parser.parse_args()

    thresholds = load_thresholds(args.thresholds)
    band = get_band(args.axis, args.value, thresholds=thresholds)

    canon = _normalize_axis_name(args.axis)
    axis_th = thresholds[canon]

    print(f"Axis: {canon}")
    print(f"Value: {args.value}")
    print(f"Thresholds: lo<{axis_th['lo']:.6f}, hi>{axis_th['hi']:.6f}")
    print(f"Band: {band}")
