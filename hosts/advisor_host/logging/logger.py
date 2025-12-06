"""
Optional JSONL logger for host events (local, file-based).
Enabled via HOST_LOG_PATH env var.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

LOG_PATH = os.environ.get("HOST_LOG_PATH")
MAX_BYTES = int(os.environ.get("HOST_LOG_MAX_BYTES", "1048576"))  # 1 MB default
BACKUPS = int(os.environ.get("HOST_LOG_BACKUPS", "3"))
ADD_CORRELATION = os.environ.get("HOST_ADD_CORRELATION_ID", "").lower() in ("1", "true", "yes")


def log_event(event: str, payload: Dict[str, Any]) -> None:
    if not LOG_PATH:
        return
    if ADD_CORRELATION and "correlation_id" not in payload:
        payload["correlation_id"] = payload.get("session_id") or payload.get("label_correlation_id")
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "data": payload,
    }
    path = Path(LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.exists() and path.stat().st_size > MAX_BYTES:
            # rotate simple backups
            for i in range(BACKUPS - 1, 0, -1):
                older = path.with_suffix(path.suffix + f".{i}")
                newer = path.with_suffix(path.suffix + f".{i+1}")
                if older.exists():
                    older.replace(newer)
            rotated = path.with_suffix(path.suffix + ".1")
            path.replace(rotated)
    except Exception:
        # best-effort; continue
        pass
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
