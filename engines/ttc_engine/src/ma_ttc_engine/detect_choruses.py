"""
Chorus detection scaffolding for TTC.

Expected inputs:
- sections/lyrics timing (future aligned data) or structural labels.
- audio-derived timing hints.

Expected outputs:
- ttc_seconds_first_chorus
- optional bar/beat offsets.

Current implementation is a stub to keep interfaces ready for future work.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Optional


def estimate_ttc(
    structure_labels: Optional[list[str]] = None,
    tempo_bpm: float | None = None,
    duration_sec: float | None = None,
    seconds_per_section_fallback: float = 12.0,
    beats_per_bar: float = 4.0,
) -> Dict[str, float]:
    """
    TTC heuristic v1:
    - Identify first chorus section by prefix "CHORUS" or label starting with "C".
    - If duration is known, allocate equal time per section; otherwise use fallback seconds per section.
    - If tempo is known, convert TTC seconds to bars (4 beats per bar).
    """
    method = "ttc_rule_based_v1"
    if not structure_labels:
        return {"ttc_seconds_first_chorus": None, "ttc_bar_position_first_chorus": None, "estimation_method": method}
    first_chorus_idx = next(
        (idx for idx, label in enumerate(structure_labels) if label.upper().startswith("CHORUS") or label.upper().startswith("C")),
        None,
    )
    if first_chorus_idx is None:
        return {"ttc_seconds_first_chorus": None, "ttc_bar_position_first_chorus": None, "estimation_method": method}
    total_sections = len(structure_labels)
    if duration_sec and total_sections > 0:
        seconds_per_section = duration_sec / total_sections
    else:
        seconds_per_section = seconds_per_section_fallback
    ttc_seconds = max(0.0, first_chorus_idx * seconds_per_section)
    bars = None
    if tempo_bpm and tempo_bpm > 0:
        beats_per_sec = tempo_bpm / 60.0
        bars = (ttc_seconds * beats_per_sec) / beats_per_bar
    confidence = "medium"
    if structure_labels and first_chorus_idx == 0:
        confidence = "low"
    if ttc_seconds == 0.0:
        confidence = "low"
    if ttc_seconds and tempo_bpm and duration_sec:
        confidence = "high"
    # Optional backend stub: allow env hook to switch method or return passthrough
    remote_mode = os.getenv("TTC_ENGINE_MODE", "local").lower()
    backend_url = os.getenv("TTC_ENGINE_URL")
    if remote_mode == "remote":
        if not backend_url:
            raise RuntimeError("TTC_ENGINE_URL is required when TTC_ENGINE_MODE=remote")
        import urllib.request

        body = json.dumps(
            {
                "structure_labels": structure_labels,
                "tempo_bpm": tempo_bpm,
                "duration_sec": duration_sec,
                "seconds_per_section_fallback": seconds_per_section_fallback,
                "beats_per_bar": beats_per_bar,
            }
        ).encode("utf-8")
        req = urllib.request.Request(backend_url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    return {
        "ttc_seconds_first_chorus": ttc_seconds,
        "ttc_bar_position_first_chorus": bars,
        "estimation_method": method,
        "ttc_confidence": confidence,
    }
