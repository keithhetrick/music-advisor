"""
Stub sidecar runner plugin for testing/CI.
Returns a fixed tempo/key payload without touching audio.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from plugins.interfaces import SidecarRunner


def factory(tempo: float = 120.0, mode: str = "minor", key: str = "C") -> SidecarRunner:
    def _run(audio: str, out: str, **kwargs) -> int:
        payload = {
            "tempo": tempo,
            "mode": mode,
            "key": key,
            "backend": "stub",
            "backend_version": "stub-1.0",
            "beats_count": 0,
        }
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
        return 0
    return _run
