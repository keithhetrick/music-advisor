#!/usr/bin/env python3
"""
Alignment utilities (stubs):
- If you have a beatgrid, we map section/line timestamps roughly to grid.
- If you have ASR word times, we roll them up to line-level.
Replace with Gentle/MFA or aeneas integration later.
"""
from typing import List, Dict, Optional

def align_lines_to_beatgrid(sections: List[Dict], first_beat_ms: Optional[int], bpm: Optional[float]) -> List[Dict]:
    """
    Naive alignment: assigns incremental timestamps per line using BPM for rough spacing.
    """
    if not bpm or not first_beat_ms:
        return [{"tag": s["tag"], "lines": s["lines"], "line_times_ms": [None]*len(s["lines"])} for s in sections]

    ms_per_beat = 60000.0 / bpm
    cursor = float(first_beat_ms)

    aligned = []
    for s in sections:
        line_times = []
        for _ in s["lines"]:
            line_times.append(int(cursor))
            # assume ~1 bar per line (4 beats) — tweak later or replace with true aligner
            cursor += ms_per_beat * 4
        aligned.append({
            "tag": s["tag"],
            "lines": s["lines"],
            "line_times_ms": line_times
        })
    return aligned

def rollup_asr_word_times(asr_words: List[Dict], sections: List[Dict]) -> List[Dict]:
    """
    If ASR yielded word-level timestamps [{word,start_ms,end_ms},...],
    we roll up to line-level min(start) for each line (very naive).
    """
    # In a real system you’d match words to lines; here we just spread them uniformly.
    idx = 0
    total = len(asr_words)
    aligned = []
    for s in sections:
        line_times = []
        for _ in s["lines"]:
            t = asr_words[idx]["start_ms"] if total and idx < total else None
            line_times.append(t)
            idx = min(idx + max(1, total // max(1, len(s["lines"]))), max(0, total-1))
        aligned.append({
            "tag": s["tag"],
            "lines": s["lines"],
            "line_times_ms": line_times
        })
    return aligned
