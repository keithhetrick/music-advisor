# MusicAdvisor/Core/commands_trend_toggle.py
import json
from pathlib import Path

FLAGS_PATH = Path("MusicAdvisor/Config/runtime_flags.json")

def _load():
    return json.loads(FLAGS_PATH.read_text())

def _save(d):
    FLAGS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2))

def trend_toggle_on():
    d = _load(); d["trend_enabled"] = True; _save(d)
    return "Trend Snapshot: ON"

def trend_toggle_off():
    d = _load(); d["trend_enabled"] = False; _save(d)
    return "Trend Snapshot: OFF"

def trend_status():
    d = _load()
    return f"Trend Snapshot: {'ON' if d.get('trend_enabled', True) else 'OFF'} (snapshot={d.get('trend_snapshot_name')})"
