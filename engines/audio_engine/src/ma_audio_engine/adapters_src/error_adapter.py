#!/usr/bin/env python3
"""
Error/guard adapter: shared helpers for safe file access and guarded JSON loading.
Keeps the pipeline resilient to oversized or malformed inputs.

Usage:
- `load_json_guarded(path, max_bytes=..., expect_mapping=True, logger=...)` to safely parse JSON with size/type guards.
- `require_file(path, logger=...)` to assert presence before proceeding.

Notes:
- Side effects: reads files only; never raises (returns None/False on failures) to keep callers resilient.
- Tuning: increase/decrease max_bytes per caller to protect against oversized inputs.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional

__all__ = [
    "load_json_guarded",
    "require_file",
]

JsonLogger = Optional[Callable[[str], None]]


def load_json_guarded(
    path: str,
    *,
    max_bytes: int | None = 5 << 20,
    expect_mapping: bool = True,
    logger: JsonLogger = None,
) -> Optional[dict[str, Any]]:
    """
    Load JSON with size/type guards.
    - max_bytes: refuse files larger than this (None to disable).
    - expect_mapping: ensure the root is a dict if True.
    """
    log = logger or (lambda _msg: None)
    try:
        if not os.path.exists(path):
            log(f"guarded json load: missing file {path}")
            return None
        size = os.path.getsize(path)
        if max_bytes is not None and size > max_bytes:
            log(f"guarded json load: refusing {path} ({size} > {max_bytes} bytes)")
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if expect_mapping and not isinstance(data, dict):
            log(f"guarded json load: expected mapping at {path}")
            return None
        return data
    except Exception as exc:  # noqa: BLE001
        log(f"guarded json load failed for {path}: {exc}")
        return None


def require_file(path: str, *, logger: JsonLogger = None) -> bool:
    """
    Return True if the path exists; log and return False otherwise.
    """
    log = logger or (lambda _msg: None)
    if os.path.exists(path):
        return True
    log(f"required file missing: {path}")
    return False
