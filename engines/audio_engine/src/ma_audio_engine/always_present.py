from __future__ import annotations
from typing import Dict, Any, List, Optional, Sequence


def _pad_axes_to_six(values: Optional[List[float]]) -> List[float]:
    if not values:
        return [0.5] * 6
    vals = list(values)
    if len(vals) < 6:
        vals.extend([0.5] * (6 - len(vals)))
    elif len(vals) > 6:
        vals = vals[:6]
    return vals


def _tempo_band(bpm: Optional[float]) -> Optional[str]:
    if bpm is None:
        return None
    lo = int(bpm // 10) * 10
    hi = lo + 9
    return f"{lo}-{hi}"


def _as_pair(x: Optional[Sequence[float]]) -> Optional[List[float]]:
    """Return [float, float] or None for spans."""
    if not x:
        return None
    if isinstance(x, (list, tuple)) and len(x) == 2:
        try:
            return [float(x[0]), float(x[1])]
        except Exception:
            return None
    return None


def coerce_payload_shape(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Guarantee a stable schema for downstream consumers & tests.
    Also exposes legacy top-level aliases: ttc_sec/ttc_conf/ttc_lift_db and tempo_bpm/band.
    """
    out = dict(raw) if isinstance(raw, dict) else {}

    # audio_axes (length = 6)
    out["audio_axes"] = _pad_axes_to_six(out.get("audio_axes"))

    # TTC block (normalized + legacy aliases)
    ttc = out.get("TTC", {}) if isinstance(out.get("TTC"), dict) else {}
    seconds = ttc.get("seconds", out.get("ttc_sec"))
    confidence = ttc.get("confidence", out.get("ttc_conf"))
    lift_db = ttc.get("lift_db", out.get("ttc_lift_db"))
    ttc_norm = {
        "seconds": seconds,
        "confidence": confidence,
        "lift_db": lift_db,
        "dropped": ttc.get("dropped", []),
        "source": ttc.get("source", "absent"),
    }
    out["TTC"] = ttc_norm
    # legacy flat aliases expected by older clients/tests
    out["ttc_sec"] = ttc_norm["seconds"]
    out["ttc_conf"] = ttc_norm["confidence"]

    # tempo block: only include dict if bpm is present; else None
    tempo = out.get("tempo")
    if isinstance(tempo, dict) and tempo.get("bpm") is not None:
        bpm = tempo.get("bpm")
        band = tempo.get("band") or _tempo_band(bpm)
        out["tempo"] = {"bpm": bpm, "band": band}
        # legacy flat aliases (nice-to-have)
        out["tempo_bpm"] = bpm
        out["tempo_band"] = band
    else:
        out["tempo"] = None
        out["tempo_bpm"] = None
        out["tempo_band"] = None

    # tonal dict presence + defaults
    tonal = out.get("tonal", {})
    if not isinstance(tonal, dict):
        tonal = {}
    tonal.setdefault("key", None)
    tonal.setdefault("mode", None)
    tonal.setdefault("confidence", None)
    tonal.setdefault("pcp", None)
    out["tonal"] = tonal

    # Spans for UI parity
    out["chorus_span"] = _as_pair(out.get("chorus_span"))
    out["verse_span"] = _as_pair(out.get("verse_span"))

    return out
