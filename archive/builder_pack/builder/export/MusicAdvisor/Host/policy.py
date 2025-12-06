from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class Policy:
    """
    Global scoring knobs (profile-scoped).
    HF-A12 defaults match the whitepaper 'normal' lane.
    """
    # Consolidation / caps
    beta_audio: float = 1.0      # lyrics advisory-only; KPI uses audio only
    cap_audio: float = 0.58      # Host cap for HCI v1

    # TTC / lift gates
    ttc_conf_gate: float = 0.60  # TTC must meet/exceed this, else TTC=NA
    lift_window_sec: float = 6.0 # ST-LUFS window for chorus-vs-verse delta

    # Canonical evaluation lane and seeds (for reproducibility)
    canonical_lane: str = "radio_us"
    seeds: List[int] = field(default_factory=lambda: [42, 314, 2718])

    # Audit switches
    emit_run_cards: bool = True
