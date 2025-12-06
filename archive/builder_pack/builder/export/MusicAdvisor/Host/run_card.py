from __future__ import annotations
import json, os, time
from dataclasses import asdict
from typing import Any, Dict, Optional
from .policy import Policy

def emit_run_card(
    out_dir: str,
    track_id: str,
    policy: Policy,
    *,
    profile: Optional[str] = None,
    lane: Optional[str] = None,
    ttc_seconds: Optional[float] = None,
    ttc_confidence: Optional[float] = None,
    lift_db: Optional[float] = None,
    dropped_features: Optional[list[str]] = None,
    notes: Optional[Dict[str, Any]] = None,
) -> str:
    os.makedirs(out_dir, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "track_id": track_id,
        "profile": profile or "default",
        "lane": lane or policy.canonical_lane,
        "policy": asdict(policy),
        "metrics": {
            "ttc_seconds": ttc_seconds,
            "ttc_confidence": ttc_confidence,
            "chorus_lift_db": lift_db,
        },
        "dropped_features": dropped_features or [],
        "notes": notes or {},
    }
    path = os.path.join(out_dir, f"{track_id}_run_card.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path
