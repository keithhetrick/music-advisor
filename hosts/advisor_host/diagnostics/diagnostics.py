"""
Diagnostics exporter: collects recent log lines, redacts sensitive fields, and packages
them for optional delivery to a support endpoint/email.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_SUPPORT_EMAIL = os.getenv("HOST_DIAGNOSTICS_EMAIL", "keith@bellweatherstudios.com")

# Keys to drop from log payloads to avoid leaking content
DROP_KEYS = {"payload", "norms", "history", "last_recommendation", "prev_recommendation"}
# Keys that are safe to keep
ALLOW_KEYS = {"event", "timestamp", "data", "metric", "value"}  # data is redacted further


def _hash_user(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


def _redact_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    safe: Dict[str, Any] = {}
    for k, v in rec.items():
        if k in DROP_KEYS:
            continue
        if k not in ALLOW_KEYS and k not in ("event", "timestamp", "data"):
            continue
        if k == "data" and isinstance(v, dict):
            filtered = {
                dk: dv
                for dk, dv in v.items()
                if dk not in DROP_KEYS and isinstance(dv, (str, int, float, bool))
            }
            safe[k] = filtered
        else:
            safe[k] = v
    return safe


def gather_diagnostics(
    log_path: Path,
    user_id: str,
    app_version: str,
    max_bytes: int = 200_000,
    max_lines: int = 400,
) -> Dict[str, Any]:
    logs: List[Dict[str, Any]] = []
    if log_path.exists():
        raw_lines = log_path.read_text(encoding="utf-8").splitlines()[-max_lines:]
        total = 0
        for line in raw_lines:
            total += len(line.encode("utf-8"))
            if total > max_bytes:
                break
            try:
                rec = json.loads(line)
                logs.append(_redact_record(rec))
            except Exception:
                continue

    return {
        "app_version": app_version,
        "user": _hash_user(user_id),
        "logs": logs,
        "support_email": DEFAULT_SUPPORT_EMAIL,
        "note": "Diagnostics are redacted and size-capped. No payload contents included.",
    }
