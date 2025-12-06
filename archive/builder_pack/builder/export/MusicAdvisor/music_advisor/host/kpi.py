from __future__ import annotations
from typing import Iterable
from .policy import Policy

def hci_v1(audio_axes: Iterable[float], policy: Policy) -> float:
    axes = list(audio_axes)
    if len(axes) != 6:
        raise ValueError(f"Expected 6 audio axes, got {len(axes)}")
    eacm = sum(axes) / 6.0
    return min(eacm, policy.cap_audio)
