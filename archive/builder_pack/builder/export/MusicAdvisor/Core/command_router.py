from __future__ import annotations

from typing import Any, Dict
from MusicAdvisor.Config.trend_toggle import trend_toggle_on, trend_toggle_off, trend_status
from MusicAdvisor.Baselines.manager import BaselineManager
from MusicAdvisor.Config.baseline_commands import baseline_pin, baseline_unpin, baseline_status

try:
    from . import advisory_router
except Exception:
    advisory_router = None

_CTX: Dict[str, Any] = {}

def _ctx() -> Dict[str, Any]:
    global _CTX
    return _CTX

def _ensure_baseline_in_ctx(region: str = "US", explicit_profile: str | None = None):
    ctx = _ctx()
    bm = BaselineManager(region=region)
    profile = {"id": explicit_profile, "effective_utc": None} if explicit_profile else bm.resolve_profile()
    bm.mark_if_changed(profile["id"])
    ctx["baseline_profile"] = profile
    ctx["baseline_changed_flag"] = bm.flag_changed()
    ctx["baseline_block"] = bm.exporter_block(profile)

def _banner_if_needed():
    ctx = _ctx()
    b = ctx.get("baseline_block") or {}
    if ctx.get("baseline_changed_flag"):
        print(f"Baseline update: {b.get('active_profile')} (effective {b.get('effective_utc')})")
    elif b.get("pinned"):
        print(f"Baseline pinned: {b.get('active_profile')}")

def build_advisor_export(hci_payload: dict) -> dict:
    if "baseline_block" not in _ctx():
        _ensure_baseline_in_ctx(region=_ctx().get("region", "US"))
    export = { **hci_payload, "Baseline": _ctx().get("baseline_block") }
    _banner_if_needed()
    return export

def handle_command(cmd: str, *args, **kwargs):
    cmd = (cmd or "").strip()
    ctx = _ctx()

    if cmd == "/trend toggle on":
        return trend_toggle_on()
    if cmd == "/trend toggle off":
        return trend_toggle_off()
    if cmd == "/trend status":
        return trend_status()

    if cmd.startswith("/baseline pin"):
        parts = cmd.split()
        profile_id = parts[-1] if len(parts) >= 3 else None
        if not profile_id:
            return "Usage: /baseline pin <profile_id>"
        return baseline_pin(profile_id, region=ctx.get("region","US"))
    if cmd == "/baseline unpin":
        return baseline_unpin(region=ctx.get("region","US"))
    if cmd == "/baseline status":
        return baseline_status(region=ctx.get("region","US"))

    if cmd.startswith("/audio map pack"):
        txt = cmd[len("/audio map pack"):].strip()
        region = ctx.get("region", "US")
        explicit_profile = None
        for token in txt.split():
            if token.startswith("region="):
                region = token.split("=",1)[1]
            if token.startswith("profile="):
                explicit_profile = token.split("=",1)[1]
        ctx["region"] = region
        _ensure_baseline_in_ctx(region=region, explicit_profile=explicit_profile)
        _banner_if_needed()
        return f"[audio] pack mapped (region={region}, profile={explicit_profile or _ctx()['baseline_profile']['id']})"

    if cmd == "/advisor export summary":
        hci_payload = kwargs.get("hci_payload", {})
        return build_advisor_export(hci_payload)

    return None
