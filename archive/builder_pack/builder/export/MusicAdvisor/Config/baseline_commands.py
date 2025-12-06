from __future__ import annotations
from MusicAdvisor.Baselines.manager import BaselineManager

def baseline_pin(profile_id: str, region: str = "US") -> str:
    bm = BaselineManager(region=region)
    bm.set_pinned_id(profile_id)
    prof = bm.resolve_profile()
    return f"Baseline pinned: {prof.get('id')}"

def baseline_unpin(region: str = "US") -> str:
    bm = BaselineManager(region=region)
    bm.set_pinned_id(None)
    prof = bm.resolve_profile()
    return f"Baseline unpinned. Active: {prof.get('id')}"

def baseline_status(region: str = "US") -> str:
    bm = BaselineManager(region=region)
    prof = bm.resolve_profile()
    pinned = "true" if bm.get_pinned_id() else "false"
    return f"Baseline: {prof.get('id')} | pinned={pinned} | effective={prof.get('effective_utc')}"
