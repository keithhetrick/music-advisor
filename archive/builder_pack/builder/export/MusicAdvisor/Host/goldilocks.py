# Host/goldilocks.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class GoldilocksConfig:
    # Priors reflect desired conversational emphasis — NOT scoring weights.
    priors_market: float = 0.50
    priors_emotional: float = 0.50
    # Soft caps: advisory strength limits (UI emphasis), not math caps on HCI.
    cap_market: float = 0.58
    cap_emotional: float = 0.58

def goldilocks_advise(
    *,
    # Inputs are *observed* subdomain summaries (post-analysis), e.g. normalized [0..1]
    observed_market: float,
    observed_emotional: float,
    cfg: Optional[GoldilocksConfig] = None,
) -> Dict[str, Any]:
    """
    Produce *advisory-only* guidance balancing Market vs Emotional narratives.
    IMPORTANT: Does not and must not change numeric HCI.
    Returns suggested emphasis deltas and a rationale string the UI can surface.
    """
    c = cfg or GoldilocksConfig()
    m = max(0.0, min(1.0, float(observed_market)))
    e = max(0.0, min(1.0, float(observed_emotional)))

    # Target narrative balance from priors (UI emphasis, not math)
    target_m = min(c.cap_market, c.priors_market)
    target_e = min(c.cap_emotional, c.priors_emotional)

    delta_m = round(target_m - m, 4)
    delta_e = round(target_e - e, 4)

    rationale = []
    if m < target_m and e > target_e:
        rationale.append("Shift modestly toward market framing while tempering emotive claims.")
    elif e < target_e and m > target_m:
        rationale.append("Lean into emotional resonance while reducing market-heavy framing.")
    elif m < target_m and e < target_e:
        rationale.append("Both narratives under-index; lift with clear market cues and emotive payoff.")
    else:
        rationale.append("Narratives within Goldilocks window; keep balance steady.")

    return {
        "advisory": {
            "target_market": target_m,
            "target_emotional": target_e,
            "delta_market": delta_m,        # + means “increase market emphasis” in UI copy/ordering
            "delta_emotional": delta_e,     # + means “increase emotional emphasis”
        },
        "rationale": " ".join(rationale),
        "safety": {
            "note": "Goldilocks is advisory-only; HCI remains unchanged."
        }
    }
