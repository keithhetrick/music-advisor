"""
Confidence adapter: normalize backend-specific confidence scores to 0–1
and derive labels consistently.

Defaults come from calibrated bounds per backend and can be overridden via
config/tempo_confidence_bounds.json (known keys only). No env flags here; callers
pass backend/bounds explicitly.

Usage:
- `normalize_tempo_confidence(raw, backend="essentia")` → 0–1 normalized
- `confidence_label(score_norm, backend="essentia", raw=raw_conf)` → "low"/"med"/"high"
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

__all__ = [
    "TEMPO_CONF_DEFAULTS",
    "normalize_tempo_confidence",
    "confidence_label",
]

TEMPO_CONF_DEFAULTS = {
    "essentia": {
        "lower": 0.93,  # p5 on benchmark_set_v1_1
        "upper": 3.63,  # p95 on benchmark_set_v1_1
        "label_low": 1.10,
        "label_high": 3.20,
    },
    "madmom": {
        "lower": 0.21,  # p5 on benchmark_set_v1_1
        "upper": 0.38,  # p95 on benchmark_set_v1_1
        "label_low": 0.23,
        "label_high": 0.33,
    },
    "librosa": {
        "lower": 0.92,  # p5 on benchmark_set_v1_1
        "upper": 0.97,  # p95 on benchmark_set_v1_1
        "label_low": 0.93,
        "label_high": 0.95,
    },
}

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "tempo_confidence_bounds.json"

try:
    if _CFG_PATH.exists():
        data = json.loads(_CFG_PATH.read_text())
        if isinstance(data, dict) and data:
            # shallow merge; only known backends are respected
            for k, v in data.items():
                if k in TEMPO_CONF_DEFAULTS and isinstance(v, dict):
                    merged = dict(TEMPO_CONF_DEFAULTS[k])
                    merged.update({ik: iv for ik, iv in v.items() if ik in merged})
                    TEMPO_CONF_DEFAULTS[k] = merged
except Exception:
    pass


def normalize_tempo_confidence(
    raw: Optional[float],
    bounds: Optional[Tuple[float, float]] = None,
    backend: Optional[str] = None,
) -> Optional[float]:
    """
    Normalize a tempo confidence score into [0, 1].
    - If bounds provided (lo, hi), use linear mapping and clamp.
    - Else use backend heuristics (Essentia often 0–4; Madmom 0–1).
    - Fallback: clamp to [0, 1].
    """
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    lo = hi = None
    if bounds and len(bounds) == 2:
        lo, hi = bounds
    else:
        backend_defaults = TEMPO_CONF_DEFAULTS.get((backend or "").lower())
        if backend_defaults:
            lo = backend_defaults["lower"]
            hi = backend_defaults["upper"]

    if lo is not None and hi is not None and hi != lo:
        try:
            lo_f, hi_f = float(lo), float(hi)
            norm = (val - lo_f) / (hi_f - lo_f)
            return max(0.0, min(1.0, norm))
        except Exception:
            pass

    backend = (backend or "").lower()
    if backend == "essentia":
        return max(0.0, min(1.0, val / 4.0))
    if backend == "madmom":
        return max(0.0, min(1.0, val))
    if backend == "librosa":
        return max(0.0, min(1.0, val))
    return max(0.0, min(1.0, val))


def confidence_label(
    score: Optional[float],
    backend: Optional[str] = None,
    raw: Optional[float] = None,
) -> Optional[str]:
    backend_lower = backend_high = None
    backend_defaults = TEMPO_CONF_DEFAULTS.get((backend or "").lower())
    if backend_defaults and raw is not None:
        backend_lower = backend_defaults["label_low"]
        backend_high = backend_defaults["label_high"]
        try:
            raw_f = float(raw)
            if raw_f >= backend_high:
                return "high"
            if raw_f >= backend_lower:
                return "med"
            return "low"
        except Exception:
            pass

    if score is None:
        return None
    if score >= 0.66:
        return "high"
    if score >= 0.33:
        return "med"
    return "low"
