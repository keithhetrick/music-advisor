from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class Policy:
    beta_audio: float = 1.0
    cap_audio: float = 0.58
    ttc_conf_gate: float = 0.60
    lift_window_sec: float = 6.0
    canonical_lane: str = "radio_us"
    seeds: List[int] = field(default_factory=lambda: [42, 314, 2718])
    emit_run_cards: bool = True
