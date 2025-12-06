# Core/engine.py
from __future__ import annotations
from typing import Dict, Any, Iterable, Optional

from music_advisor.host.policy import Policy
from music_advisor.host.kpi import hci_v1

def _maybe_axes(staged: Dict[str, Any]) -> Optional[Iterable[float]]:
    # Accept several common shapes from the Automator/extractor
    for key in ("audio_axes", "axes", "AUDIO.axes", "features.audio_axes"):
        v = staged.get(key)
        if isinstance(v, (list, tuple)) and len(v) == 6:
            try:
                vals = [float(x) for x in v]
                if all(0.0 <= x <= 1.0 for x in vals):
                    return vals
            except Exception:
                pass
    return None

def _fallback_hci_from_mvp(staged: Dict[str, Any]) -> float:
    """
    Legacy, deterministic fallback when we don't have six axes yet.
    Mirrors your previous simple 'presence' heuristic but enforces the host cap.
    """
    mvp = staged.get("MVP") or staged.get("mvp") or {}
    have = sum(
        1
        for k in ("tempo_bpm", "tempo_band_bpm", "runtime_sec", "ttc_sec", "exposures")
        if mvp.get(k) is not None
    )
    base = min(0.58, 0.30 + 0.06 * have)  # max aligns with host cap
    return float(base)

def run_hci(staged: Dict[str, Any], policy: Optional[Policy] = None) -> Dict[str, Any]:
    """
    Returns a deterministic HCI_v1 block.
    Preferred path: compute from six audio axes via host KPI (cap at host boundary).
    Fallback: legacy MVP presence model (still capped).
    """
    pol = policy or Policy()

    axes = _maybe_axes(staged)
    if axes is not None:
        score = hci_v1(axes, pol)  # single source of truth, cap at 0.58 by default
    else:
        score = _fallback_hci_from_mvp(staged)

    hci = {
        "HCI_v1_score": round(float(score), 4),
        "cap_audio": pol.cap_audio,
        "beta_audio": pol.beta_audio,
    }
    return {"HCI_v1": hci}
