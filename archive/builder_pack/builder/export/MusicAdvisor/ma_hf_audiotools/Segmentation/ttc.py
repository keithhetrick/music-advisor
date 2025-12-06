from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Sequence, Dict, Any

from music_advisor.host.policy import Policy
from ma_hf_audiotools.Features.loudness import chorus_lift_db

@dataclass
class SegmentationResult:
    ttc_seconds: Optional[float]
    ttc_confidence: Optional[float]
    verse_span: Optional[Tuple[float, float]]
    chorus_span: Optional[Tuple[float, float]]

def detect_ttc_stub(signal: Sequence[float], sr: int) -> SegmentationResult:
    """
    Placeholder TTC detector. Replace with your production detector.
    Defaults to low confidence to exercise gating logic.
    """
    return SegmentationResult(
        ttc_seconds=None,
        ttc_confidence=0.40,
        verse_span=None,
        chorus_span=None,
    )

def apply_ttc_gate_and_lift(
    signal: Sequence[float],
    sr: int,
    seg: SegmentationResult,
    policy: Policy,
) -> Dict[str, Any]:
    """
    Apply TTC confidence gate and compute/dismiss chorus lift accordingly.
    Returns:
      {
        "ttc_seconds": Optional[float],  # None if gated
        "ttc_confidence": Optional[float],
        "lift_db": Optional[float],      # None if gated/invalid
        "drop_features": list[str],      # e.g., ["chorus_lift"]
      }
    """
    drop: list[str] = []
    ttc_sec = seg.ttc_seconds
    ttc_conf = seg.ttc_confidence

    if ttc_conf is None or ttc_conf < policy.ttc_conf_gate:
        # TTC rejected — set TTC=NA and drop dependent subfeatures
        ttc_sec_out = None
        drop.append("chorus_lift")
        lift = None
    else:
        ttc_sec_out = ttc_sec
        if seg.verse_span and seg.chorus_span:
            lift = chorus_lift_db(
                signal, sr, seg.verse_span, seg.chorus_span, policy.lift_window_sec
            )
            if lift is None:
                drop.append("chorus_lift")
        else:
            lift = None
            drop.append("chorus_lift")

    return {
        "ttc_seconds": ttc_sec_out,
        "ttc_confidence": ttc_conf,
        "lift_db": lift,
        "drop_features": drop,
    }
