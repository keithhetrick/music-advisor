from __future__ import annotations
from typing import Any, Dict, List, Optional

def normalize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts v0.3.5 payload; provides backward-compat for older flat TTC keys if present.
    """
    out = dict(data)

    # Back-compat shim: map flat keys to nested TTC
    if "TTC" not in out:
        out["TTC"] = {
            "seconds": out.get("ttc_sec"),
            "confidence": out.get("ttc_conf"),
            "lift_db": out.get("ttc_lift_db"),
            "dropped": out.get("ttc_dropped", []),
            "source": out.get("ttc_source", "unknown")
        }

    # Ensure axes padded to 6
    axes = out.get("audio_axes", [])
    if len(axes) < 6:
        axes = list(axes) + [0.5] * (6 - len(axes))
    out["audio_axes"] = axes[:6]

    # Ensure tempo block exists
    if "tempo" not in out:
        out["tempo"] = {"bpm": None, "band_10s": None}

    # Ensure tonal.confidence present
    tonal = out.get("tonal", {})
    tonal["confidence"] = tonal.get("confidence", None)
    out["tonal"] = tonal

    return out
