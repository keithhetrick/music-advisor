# Axes definitions for ma_audio_engine.
"""
Six-axis composer for Audio Intelligence.
- Computes axes from features
- Applies baseline normalization (z-features)
- Applies tiny Market prior nudge (bounded), without changing caps/gates
"""

from typing import Dict, Any, List
from ma_audio_engine.host.baseline_normalizer import normalize_features
from ma_audio_engine.host.baseline_loader import load_baseline
from ma_audio_engine.policy import BASELINE_INFLUENCE

# Choose which index is the "Market/Commercial Fit" axis in your 6 axes
IDX_MARKET = 1  # example: [AudioCraft, Market, Energy, Groove, Tonal, Dynamics]
                 # adjust to your actual order

def _tempo_band_of(bpm: float) -> str:
    """
    Map a BPM to a 10-BPM band label like "110–119".
    """
    lo = int(bpm // 10) * 10
    hi = lo + 9
    return f"{lo}–{hi}"

def _safe_unit(x: float) -> float:
    return 0.0 if x is None else max(0.0, min(1.0, float(x)))

def _compute_base_axes(feat: Dict[str, Any]) -> List[float]:
    """
    Your existing axis math goes here.
    The sample below is placeholder math—replace with your real computations.
    """
    # Example placeholders (replace with real formulas):
    # A1: Audio craft (dummy: inverse loudness penalty)
    loud = float(feat.get("loudness_lufs", -12.0))
    a1 = _safe_unit(0.5 + (-(loud + 14.0)) * 0.01)

    # A2: Market (pre-prior raw estimate; e.g., based on structure/clarity/etc.)
    a2 = _safe_unit(0.50)

    # A3: Energy (dummy: based on energy feature)
    a3 = _safe_unit(float(feat.get("energy", 0.5)))

    # A4: Groove (dummy: based on danceability)
    a4 = _safe_unit(float(feat.get("danceability", 0.5)))

    # A5: Tonal appeal (dummy: major/minor heuristic)
    a5 = 0.60 if str(feat.get("mode","major")).lower() == "major" else 0.45

    # A6: Dynamics/contrast (dummy: neutral)
    a6 = 0.50

    return [a1, a2, a3, a4, a5, a6]

def _market_prior_nudge(features: Dict[str, Any], market_axis_value: float) -> float:
    """
    Apply a tiny, bounded nudge toward cohort preferences for tempo band and key.
    This is advisory-strength only; NEVER touches caps/gates.
    """
    w = float(BASELINE_INFLUENCE.get("market_prior_weight", 0.0))
    clamp = float(BASELINE_INFLUENCE.get("max_prior_delta", 0.0))
    if w <= 0.0 or clamp <= 0.0:
        return market_axis_value

    b = load_baseline()
    if not b:
        return market_axis_value

    norms = b.get("MARKET_NORMS", {})
    bands = set(norms.get("tempo_band_pref", []) or [])
    keydist = norms.get("key_distribution", {}) or {}

    delta = 0.0

    # tempo band prior
    bpm = features.get("bpm")
    if isinstance(bpm, (int, float)) and bands:
        band = _tempo_band_of(float(bpm))
        if band in bands:
            delta += 0.5 * w * clamp  # up to half clamp if band preferred

    # key prior
    key = features.get("key")
    if isinstance(key, str) and keydist:
        p = float(keydist.get(key, 0.0))
        # map probability to tiny nudge, capped at half clamp
        delta += min(p * w, 0.5 * clamp)

    # clamp the total delta
    if delta > 0:
        delta = min(delta, clamp)
    else:
        delta = max(delta, -clamp)

    return _safe_unit(market_axis_value + delta)

def compute_axes(features: Dict[str, Any]) -> List[float]:
    """
    Public entry: normalize features, compute axes, then apply market prior.
    """
    fz = normalize_features(features)   # adds bpm_z/runtime_z + cohort priors
    axes = _compute_base_axes(fz)

    # apply the gentle Market prior nudge ONLY to the Market axis
    axes[IDX_MARKET] = _market_prior_nudge(fz, axes[IDX_MARKET])
    return axes
