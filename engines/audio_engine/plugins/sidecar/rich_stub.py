"""
Richer stub sidecar: returns tempo/key plus beat grid and confidence meta.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

def factory(tempo: float = 120.0, mode: str = "minor", key: str = "C", beats: Optional[list] = None, conf: float = 0.8):
    beats = beats or [0.0, 0.5, 1.0, 1.5]
    def _run(audio: str, out: str, **kwargs) -> int:
        payload = {
            "tempo": tempo,
            "tempo_confidence_score": conf,
            "tempo_confidence_bounds": [0.9, 3.6],
            "mode": mode,
            "key": key,
            "backend": "stub",
            "backend_version": "stub-1.0",
            "beats_sec": beats,
            "beats_count": len(beats),
        }
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
        return 0
    return _run
