from __future__ import annotations
from typing import Iterable
from .policy import Policy

def hci_v1(audio_axes: Iterable[float], policy: Policy) -> float:
    """
    Single source of truth for KPI (audio-only, v1).
    HCI = min(mean(audio_axes), cap_audio).
    - Cap is applied at Host only.
    - Lyrics are advisory-only under HF-A12 (beta_audio=1.0).
    """
    axes = list(audio_axes)
    if len(axes) != 6:
        raise ValueError(f"Expected 6 audio axes, got {len(axes)}")
    eacm = sum(axes) / 6.0
    return min(eacm, policy.cap_audio)
