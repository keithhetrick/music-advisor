# Baseline normalizer for ma_audio_engine host helpers.
from __future__ import annotations
import math
from typing import Dict, Any, List

def _gaussian_window(center: float, std: float, x: float) -> float:
    if std is None or std <= 0:  # avoid div-by-zero; fallback neutral 0.5 if unknown
        return 0.5
    z = (x - center) / std
    return math.exp(-0.5 * z * z)

def summarize_market_fit(m: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MARKET_NORMS to human-friendly advisory (windows, keys, bands).
    Does not change scoring—purely advisory.
    """
    out: Dict[str, Any] = {"Market_Fit": {}, "tempo": {}, "key": {}, "runtime": {}}

    # Tempo bands
    mu = m.get("tempo_bpm_mean")
    sd = m.get("tempo_bpm_std")
    bands: List[str] = m.get("tempo_band_pref") or []
    if mu and sd:
        out["Market_Fit"]["tempo_window"] = f"{int(mu-1*sd)}–{int(mu+1*sd)}"
    if bands:
        out["tempo"]["preferred_bands"] = bands
    if mu:
        out["tempo"]["center_bpm"] = float(mu)
        out["tempo"]["suggested_window_bpm"] = out["Market_Fit"].get("tempo_window")

    # Keys / modes
    kd: Dict[str, float] = m.get("key_distribution") or {}
    if kd:
        top = sorted(kd.items(), key=lambda x: x[1], reverse=True)[:5]
        out["Market_Fit"]["top_keys"] = [k for k, _ in top]
        out["key"]["top_keys"] = [k for k, _ in top]
        out["key"]["top_keys_with_weights"] = [{"key": k, "p": round(p, 2)} for k, p in top]

    mr = m.get("mode_ratio") or {}
    if mr:
        maj = int(round((mr.get("major", 0)*100)))
        minr = int(round((mr.get("minor", 0)*100)))
        out["Market_Fit"]["mode_pref"] = f"major {maj}% / minor {minr}%"

    # Runtime
    rmu = m.get("runtime_sec_mean")
    rsd = m.get("runtime_sec_std")
    if rmu and rsd:
        lo = int(round(rmu - rsd))
        hi = int(round(rmu + rsd))
        out["runtime"]["suggested_window_sec"] = [lo, hi]
        out["runtime"]["center_sec"] = float(rmu)
        out["runtime"]["suggested_window_human"] = f"{lo}–{hi} s"

    return out
