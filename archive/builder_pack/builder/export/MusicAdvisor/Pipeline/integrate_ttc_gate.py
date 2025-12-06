# Pipeline/integrate_ttc_gate.py
from __future__ import annotations
from typing import Sequence, Dict, Any, Optional, Tuple

from music_advisor.host.policy import Policy
from ma_hf_audiotools.Segmentation import (
    SegmentationResult,
    apply_ttc_gate_and_lift,
)
from .ttc_synth import TTCInputs, synthesize_ttc_confidence

def _coerce_span(x: Optional[Tuple[float,float]]) -> Optional[Tuple[float,float]]:
    if not x:
        return None
    return (float(x[0]), float(x[1]))

def integrate_ttc_gate_and_chorus_lift(
    signal: Sequence[float],
    sr: int,
    seg: SegmentationResult,
    axis,
    policy: Policy | None = None,
    *,
    # optional raw hints if seg lacks confidence
    ttc_real: Optional[float] = None,
    ttc_lyrics: Optional[float] = None,
    verse_span: Optional[Tuple[float,float]] = None,
    chorus_span: Optional[Tuple[float,float]] = None,
) -> Dict[str, Any]:
    """
    Pipeline hook:
      A) If seg.ttc_confidence is None, synthesize TTC and confidence from available hints (audio/lyrics).
      B) Gate TTC using policy.ttc_conf_gate.
      C) If gated or spans invalid -> drop 'chorus_lift' subfeature; else set it.

    Returns the gate payload for audit:
      { "ttc_seconds", "ttc_confidence", "lift_db", "drop_features": [...] , "source": "audio|lyrics|none" }
    """
    pol = policy or Policy()

    # If upstream gave us no conf, synthesize a reasonable one
    src = "upstream"
    seg_in = seg
    if seg.ttc_confidence is None:
        synth = synthesize_ttc_confidence(
            TTCInputs(
                ttc_real=ttc_real,
                ttc_lyrics=ttc_lyrics,
                verse_span=_coerce_span(verse_span),
                chorus_span=_coerce_span(chorus_span),
            )
        )
        seg_in = SegmentationResult(
            ttc_seconds=synth["ttc_seconds"],
            ttc_confidence=synth["ttc_confidence"],
            verse_span=synth["verse_span"],
            chorus_span=synth["chorus_span"],
        )
        src = synth["source"]

    gate = apply_ttc_gate_and_lift(signal, sr, seg_in, pol)
    gate["source"] = src

    if "chorus_lift" in gate["drop_features"]:
        if hasattr(axis, "drop_subfeature"):
            axis.drop_subfeature("chorus_lift")
        if hasattr(axis, "renormalize"):
            axis.renormalize()
    else:
        if hasattr(axis, "set_subfeature"):
            axis.set_subfeature("chorus_lift", gate["lift_db"])

    return gate
