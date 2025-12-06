# Baseline loader for ma_audio_engine host helpers.
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_BASELINE = "datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json"

def load_baseline(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load frozen baseline (μ/σ and categorical priors).
    If missing, return None (caller must handle safe defaults).
    """
    p = path or os.environ.get("BASELINE_PATH", DEFAULT_BASELINE)
    pth = Path(p)
    if not pth.exists():
        return None
    try:
        d = json.loads(pth.read_text())
        d.setdefault("id", pth.name)
        return d
    except Exception:
        return None
