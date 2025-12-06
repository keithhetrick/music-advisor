from __future__ import annotations
import math
from typing import Tuple, Optional, Sequence

def _rms(x):
    return math.sqrt(sum(s*s for s in x) / max(1, len(x)))

def _to_lufs(rms: float) -> float:
    if rms <= 1e-12:
        return -120.0
    return 20.0 * math.log10(rms + 1e-12)

def _slice(sig: Sequence[float], sr: int, t0: float, t1: float):
    i0 = max(0, int(t0 * sr))
    i1 = min(len(sig), int(t1 * sr))
    return sig[i0:i1]

def short_term_loudness_lufs(
    signal: Sequence[float], sr: int, center_time: float, window_sec: float
) -> float:
    half = window_sec / 2.0
    seg = _slice(signal, sr, center_time - half, center_time + half)
    return _to_lufs(_rms(seg))

def chorus_lift_db(
    signal: Sequence[float],
    sr: int,
    verse_span: Tuple[float, float],
    chorus_span: Tuple[float, float],
    window_sec: float,
) -> Optional[float]:
    if (verse_span[1] - verse_span[0]) < window_sec or (chorus_span[1] - chorus_span[0]) < window_sec:
        return None
    v_center = (verse_span[0] + verse_span[1]) / 2.0
    c_center = (chorus_span[0] + chorus_span[1]) / 2.0
    verse_lufs = short_term_loudness_lufs(signal, sr, v_center, window_sec)
    chorus_lufs = short_term_loudness_lufs(signal, sr, c_center, window_sec)
    return chorus_lufs - verse_lufs
