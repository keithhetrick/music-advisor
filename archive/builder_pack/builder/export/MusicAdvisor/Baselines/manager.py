from __future__ import annotations
from typing import Optional, Dict
from pathlib import Path
import json

from .repository import fetch, fetch_default_for_region

STATE_PATH = Path("MusicAdvisor/Config/baseline_state.json")

def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_state(d: dict):
    STATE_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

class BaselineManager:
    def __init__(self, region: str = "US"):
        self.region = region
        self.state = _load_state()

    def get_pinned_id(self) -> Optional[str]:
        return self.state.get("pinned_profile_id")

    def set_pinned_id(self, profile_id: Optional[str]):
        if profile_id:
            self.state["pinned_profile_id"] = profile_id
        else:
            self.state.pop("pinned_profile_id", None)
        _save_state(self.state)

    def resolve_profile(self) -> dict:
        pinned = self.get_pinned_id()
        prof = fetch(pinned) if pinned else fetch_default_for_region(self.region)
        return prof

    def mark_if_changed(self, current_id: str) -> bool:
        last = self.state.get("last_used_profile_id")
        pinned = self.get_pinned_id() is not None
        changed = (not pinned) and bool(last) and last != current_id
        if changed:
            self.state["previous_profile_id"] = last
            self.state["baseline_changed_flag"] = True
        else:
            self.state["baseline_changed_flag"] = False
        self.state["last_used_profile_id"] = current_id
        _save_state(self.state)
        return changed

    def flag_changed(self) -> bool:
        return bool(self.state.get("baseline_changed_flag"))

    def exporter_block(self, profile: dict) -> dict:
        return {
            "active_profile": profile.get("id"),
            "effective_utc": profile.get("effective_utc"),
            "previous_profile": self.state.get("previous_profile_id"),
            "pinned": bool(self.get_pinned_id()),
            "note": "HCI_v1 model unchanged; MARKET_NORMS refreshed."
        }
