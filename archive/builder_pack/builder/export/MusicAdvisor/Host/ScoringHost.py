from __future__ import annotations
from typing import Sequence, Optional, Dict, Any

from music_advisor.host.policy import Policy
from music_advisor.host.kpi import hci_v1
from music_advisor.host.run_card import emit_run_card
from ma_hf_audiotools.Segmentation import SegmentationResult, apply_ttc_gate_and_lift

def compute_hci_and_gate_ttc(
    *,
    signal: Sequence[float],
    sr: int,
    seg: SegmentationResult,
    audio_axes: Sequence[float],
    track_id: str = "track",
    profile: str = "US_Pop_2025",
    policy: Optional[Policy] = None,
    emit_card: bool = True,
    run_card_dir: str = "out/run_cards",
    extra_notes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pol = policy or Policy()

    gate = apply_ttc_gate_and_lift(signal, sr, seg, pol)
    HCI = hci_v1(audio_axes, pol)

    if emit_card:
        emit_run_card(
            out_dir=run_card_dir,
            track_id=track_id,
            policy=pol,
            profile=profile,
            lane=pol.canonical_lane,
            ttc_seconds=gate["ttc_seconds"],
            ttc_confidence=gate["ttc_confidence"],
            lift_db=gate["lift_db"],
            dropped_features=gate["drop_features"],
            notes={**(extra_notes or {}), "HCI": HCI},
        )

    return {"HCI": HCI, "policy": {"cap_audio": pol.cap_audio, "ttc_conf_gate": pol.ttc_conf_gate, "lift_window_sec": pol.lift_window_sec}, "gate": gate}
