import json
from pathlib import Path

FLAGS_PATH = Path("MusicAdvisor/Config/runtime_flags.json")

def _load():
    try:
        return json.loads(FLAGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"trend_enabled": True, "trend_snapshot_name": None}

def _save(d: dict):
    FLAGS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def trend_toggle_on():
    d = _load(); d["trend_enabled"] = True; _save(d)
    return "✅ Trend Snapshot: ON"

def trend_toggle_off():
    d = _load(); d["trend_enabled"] = False; _save(d)
    return "✅ Trend Snapshot: OFF"

def trend_status():
    d = _load()
    state = "ON" if d.get("trend_enabled", True) else "OFF"
    return f"Trend Snapshot: {state} (snapshot={d.get('trend_snapshot_name')})"
