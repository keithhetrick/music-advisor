"""
Exporter plugin that echoes payload to stdout (JSON), useful for debugging.
"""
from __future__ import annotations

import json
from pathlib import Path


def factory():
    def _export(payload: dict, path: Path) -> None:
        print(json.dumps({"path": str(path), "payload": payload}))
    return _export
