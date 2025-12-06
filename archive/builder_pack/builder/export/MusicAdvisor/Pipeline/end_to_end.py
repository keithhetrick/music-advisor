# Pipeline/end_to_end.py

from __future__ import annotations
from typing import Any, Dict, Optional, Sequence, Tuple

from Advisor.exporter import build_advisor_export
from Host.policy import Policy as HostPolicy
from ma_hf_audiotools.Segmentation import SegmentationResult, apply_ttc_gate_and_lift


def _mean(xs: Sequence[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else 0.0


def score_from_extractor_payload(raw: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    End-to-end score from an extractor-style payload.

    Expected `raw` keys (some optional):
      - audio_axes: list[float] (ideally length 6)
      - ttc_sec: Optional[float]
      - ttc_conf: Optional[float]
      - ttc_lyrics: Optional[float]  (fallback TTC if real TTC is absent; conf=0.50)
      - verse_span: Optional[list[float, float]]
      - chorus_span: Optional[list[float, float]]
      - sr: int
      - signal: Optional[Sequence[float]]

    Optional kwargs:
      - observed_market: float (0..1), for Goldilocks advisory
      - observed_emotional: float (0..1), for Goldilocks advisory
      - policy: HostPolicy override
    """
    observed_market = float(kwargs.get("observed_market", 0.50))
    observed_emotional = float(kwargs.get("observed_emotional", 0.50))
    pol: HostPolicy = kwargs.get("policy") or HostPolicy()

    # ---- Axes / HCI ---------------------------------------------------------
    axes = [float(x) for x in raw.get("audio_axes", [])]
    eacm = _mean(axes)
    hci = min(eacm, float(pol.cap_audio))  # Host cap only

    # ---- TTC assembly (real or lyric-synth) --------------------------------
    ttc_sec: Optional[float] = raw.get("ttc_sec")
    ttc_conf: Optional[float] = raw.get("ttc_conf")
    source = "upstream"

    if ttc_sec is None:
        lyr = raw.get("ttc_lyrics")
        if lyr is not None:
            ttc_sec = float(lyr)
            ttc_conf = 0.50  # lyric-tier confidence
            source = "lyrics_synth"
        else:
            ttc_conf = None
            source = "absent"

    verse_span = raw.get("verse_span")
    chorus_span = raw.get("chorus_span")
    sr = int(raw.get("sr", 44100))
    signal = raw.get("signal", [0.0] * sr)

    seg = SegmentationResult(
        ttc_seconds=ttc_sec,
        ttc_confidence=ttc_conf,
        verse_span=tuple(verse_span) if verse_span else None,
        chorus_span=tuple(chorus_span) if chorus_span else None,
    )

    gate = apply_ttc_gate_and_lift(signal, sr, seg, pol)
    # Ensure a source is present for traceability
    gate.setdefault("source", source)

    # Top-level TTC block expected by tests (aliasing the gating result)
    ttc_block = {
        "seconds": gate.get("ttc_seconds"),
        "confidence": gate.get("ttc_confidence"),
        "lift_db": gate.get("lift_db"),
        "dropped": list(gate.get("drop_features", [])),
        "source": gate.get("source"),
    }

    # ---- Structural gates (advisory; never mutate HCI numbers) -------------
    drop_feats = []
    if gate.get("ttc_seconds") is None:
        drop_feats.append("chorus_lift")

    use_exposures = False  # v1.1 advisory-only; off by default
    if not use_exposures:
        drop_feats.append("exposures")

    structural = {
        "drop": drop_feats,
        "notes": {
            "struct_mode": "optional",
            "struct_reliable": False,
            "use_ttc": True,
            "use_exposures": use_exposures,
            "ttc_gate_threshold": float(pol.ttc_conf_gate),
            "reasoning": "Subfeatures dropped due to structural eligibility, not numeric HCI logic.",
        },
    }

    # ---- Goldilocks advisory (does not change HCI) --------------------------
    target_market = 0.50
    target_emotional = 0.50
    goldilocks = {
        "advisory": {
            "target_market": target_market,
            "target_emotional": target_emotional,
            "delta_market": target_market - observed_market,
            "delta_emotional": target_emotional - observed_emotional,
        },
        "rationale": "Shift modestly toward market framing while tempering emotive claims.",
        "safety": {"note": "Goldilocks is advisory-only; HCI remains unchanged."},
    }

    # ---- Context for exporter / final assembly ------------------------------
    ctx = {
        "Policy": {
            "cap_audio": float(pol.cap_audio),
            "ttc_conf_gate": float(pol.ttc_conf_gate),
            "lift_window_sec": float(pol.lift_window_sec),
        },
        "TTC_Gate": {
            "ttc_seconds": gate.get("ttc_seconds"),
            "ttc_confidence": gate.get("ttc_confidence"),
            "lift_db": gate.get("lift_db"),
            "drop_features": gate.get("drop_features", []),
            "source": gate.get("source"),
        },
        "TTC": ttc_block,
        "Structural_Gates": structural,
        "Structural": structural,  # legacy alias
        "Goldilocks": goldilocks,
        "Axes": {"audio_axes": axes},
    }

    # Base export (adds Baseline). Never mutates HCI numbers.
    export = build_advisor_export({"HCI_v1": {"HCI_v1_score": float(hci)}}, ctx)

    # Attach advisory/context blocks for the final payload shape
    export.update({
        "Policy": ctx["Policy"],
        "TTC_Gate": ctx["TTC_Gate"],
        "TTC": ttc_block,
        "Structural_Gates": ctx["Structural_Gates"],
        "Structural": ctx["Structural"],
        "Goldilocks": ctx["Goldilocks"],
        "Axes": ctx["Axes"],
    })

    return export
