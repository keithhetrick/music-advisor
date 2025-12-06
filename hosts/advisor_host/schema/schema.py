import json
from pathlib import Path
from typing import Any, Dict

"""
Minimal reply schema helpers.
"""


SCHEMA_PATH = Path(__file__).with_name("reply_schema.json")
try:
    SCHEMA = json.loads(SCHEMA_PATH.read_text())
except Exception:
    SCHEMA = None

def validate_reply_shape(resp: Dict[str, Any]) -> None:
    if SCHEMA is None:
        # fallback minimal checks
        if not isinstance(resp, dict):
            raise ValueError("Response must be a dict")
        for key in ("session_id", "reply", "ui_hints"):
            if key not in resp:
                raise ValueError(f"Missing required field: {key}")
        ui = resp.get("ui_hints") or {}
        for key in ("show_cards", "quick_actions", "tone", "primary_slices"):
            if key not in ui:
                raise ValueError(f"Missing ui_hints field: {key}")
    else:
        # basic manual validation against loaded schema (no external deps)
        for key in SCHEMA.get("required", []):
            if key not in resp:
                raise ValueError(f"Missing required field: {key}")
        ui = resp.get("ui_hints") or {}
        for key in SCHEMA["properties"]["ui_hints"].get("required", []):
            if key not in ui:
                raise ValueError(f"Missing ui_hints field: {key}")


__all__ = ["validate_reply_shape"]
