# Host/structural_policy.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class StructuralPolicy:
    # toggles are “can use” (eligibility) — not hard math operations on HCI
    use_ttc: bool = True
    use_exposures: bool = False
    reliable: bool = False      # UI hint only; does not change HCI
    mode: str = "optional"      # "optional" | "strict" (advisory semantics)

def structural_gates(
    *,
    policy: StructuralPolicy,
    ttc_confidence: float | None,
    ttc_gate_threshold: float,
    available_subfeatures: List[str],
) -> Dict[str, Any]:
    """
    Decide which subfeatures are eligible to contribute to axis assembly.
    Returns a dict with 'drop' list and 'notes' for audit/UI.
    """
    drops: List[str] = []

    # TTC-gated subfeatures
    if "chorus_lift" in available_subfeatures:
        if (not policy.use_ttc) or (ttc_confidence is None) or (ttc_confidence < ttc_gate_threshold):
            drops.append("chorus_lift")

    # Exposures-controlled subfeatures (example)
    if "exposures" in available_subfeatures and (not policy.use_exposures):
        drops.append("exposures")

    notes = {
        "struct_mode": policy.mode,
        "struct_reliable": policy.reliable,
        "use_ttc": policy.use_ttc,
        "use_exposures": policy.use_exposures,
        "ttc_gate_threshold": ttc_gate_threshold,
        "reasoning": "Subfeatures dropped due to structural eligibility, not numeric HCI logic.",
    }
    return {"drop": drops, "notes": notes}
