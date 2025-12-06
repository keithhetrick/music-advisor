from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Dict

DEFAULTS: Dict[str, str] = { "US": "US_Pop_2025" }
DATA_DIR = Path("MusicAdvisor/_Archive/Data")

def _meta_path(profile_id: str) -> Path:
    return DATA_DIR / f"{profile_id}.meta.json"

def fetch(profile_id: str) -> Optional[dict]:
    if not profile_id:
        return None
    mp = _meta_path(profile_id)
    if mp.exists():
        try:
            meta = json.loads(mp.read_text(encoding="utf-8"))
            if "id" not in meta:
                meta["id"] = profile_id
            return meta
        except Exception:
            pass
    eff = "2025-11-01T00:00:00Z" if "2025" in profile_id else None
    return {"id": profile_id, "effective_utc": eff}

def fetch_default_for_region(region: str) -> dict:
    pid = DEFAULTS.get(region, DEFAULTS["US"])
    return fetch(pid)
