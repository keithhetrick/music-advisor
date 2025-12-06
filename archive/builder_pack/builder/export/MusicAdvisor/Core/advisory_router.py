"""
MusicAdvisor v1.1 — Advisory Router (toggle-aware)
- HCI: primary scoring (untouched)
- Trend Snapshot: advisory-only (can toggle ON/OFF)
- CreatorPulse: identity flavor (advisory/optimization only)
- Lyric analysis: advisory-only (never affects HCI)
"""

from pathlib import Path
import json

from .listener_models import map_listener_timeless, map_listener_trend_aware
from .era_models import map_era_timeless, map_era_trend_aware
from .emotion_models import emotion_scan_timeless, emotion_scan_trend_aware
from .biome_models import biome_classify_timeless, biome_classify_trend_aware
from .endurance_models import endurance_test_timeless, endurance_test_trend_aware
from .optimization_models import build_optimization_plan_timeless, build_optimization_plan_trend_informed
from .lyric_advisor import lyric_advisory

FLAGS_PATH = Path("MusicAdvisor/Config/runtime_flags.json")

def _flags():
    try:
        return json.loads(FLAGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"trend_enabled": True, "trend_snapshot_name": None}

def advisory_context(track_features, hci_results, trend_store: dict, creator_pulse=None):
    flags = _flags()
    ctx = {
        "hci": hci_results,
        "features": track_features,
        "trend_enabled": bool(flags.get("trend_enabled", True)),
        "trend_snapshot_name": flags.get("trend_snapshot_name"),
        "creator_pulse": creator_pulse
    }
    if ctx["trend_enabled"]:
        snap = ctx["trend_snapshot_name"]
        ctx["trend"] = trend_store.get(snap) if snap in trend_store else None
    else:
        ctx["trend"] = None
    return ctx

def era_map(ctx):
    if ctx["trend"] is None:
        return map_era_timeless(ctx["features"], ctx["hci"])
    return map_era_trend_aware(ctx["features"], ctx["hci"], ctx["trend"])

def listener_map(ctx):
    if ctx["trend"] is None:
        return map_listener_timeless(ctx["features"], ctx["hci"])
    return map_listener_trend_aware(ctx["features"], ctx["hci"], ctx["trend"])

def emotion_scan(ctx):
    if ctx["trend"] is None:
        return emotion_scan_timeless(ctx["features"], ctx["hci"])
    return emotion_scan_trend_aware(ctx["features"], ctx["hci"], ctx["trend"])

def biome_classify(ctx):
    if ctx["trend"] is None:
        return biome_classify_timeless(ctx["features"], ctx["hci"])
    return biome_classify_trend_aware(ctx["features"], ctx["hci"], ctx["trend"])

def endurance_test(ctx):
    if ctx["trend"] is None:
        return endurance_test_timeless(ctx["features"], ctx["hci"])
    return endurance_test_trend_aware(ctx["features"], ctx["hci"], ctx["trend"])

def build_optimization(ctx):
    if ctx["trend"] is None:
        return build_optimization_plan_timeless(ctx["features"], ctx["hci"])
    return build_optimization_plan_trend_informed(
        ctx["features"], ctx["hci"], ctx["trend"], ctx["creator_pulse"]
    )

def lyric_notes(ctx):
    # Advisory only — do not route trend into lyrics for v1.1
    return lyric_advisory(ctx["features"], ctx["hci"])

def run_advisory_modules(track_features, hci_results, trend_store, creator_pulse=None):
    ctx = advisory_context(track_features, hci_results, trend_store, creator_pulse)
    return {
        "era":       era_map(ctx),
        "listener":  listener_map(ctx),
        "emotion":   emotion_scan(ctx),
        "biome":     biome_classify(ctx),
        "endurance": endurance_test(ctx),
        "lyric":     lyric_notes(ctx),
        "optimization": build_optimization(ctx),
    }
