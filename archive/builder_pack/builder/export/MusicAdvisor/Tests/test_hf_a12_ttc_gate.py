from ma_hf_audiotools.Segmentation import SegmentationResult, apply_ttc_gate_and_lift
from music_advisor.host.policy import Policy

def test_ttc_gated_drops_lift():
    sig = [0.0]*48000; sr = 48000
    seg = SegmentationResult(ttc_seconds=12.3, ttc_confidence=0.55, verse_span=(10.0,16.0), chorus_span=(30.0,36.0))
    out = apply_ttc_gate_and_lift(sig, sr, seg, Policy(ttc_conf_gate=0.60))
    assert out["ttc_seconds"] is None
    assert "chorus_lift" in out["drop_features"]

def test_ttc_passes_and_attempts_lift():
    sig = [0.0]*48000; sr = 48000
    seg = SegmentationResult(ttc_seconds=15.0, ttc_confidence=0.75, verse_span=(10.0,20.0), chorus_span=(30.0,40.0))
    out = apply_ttc_gate_and_lift(sig, sr, seg, Policy(lift_window_sec=6.0))
    assert out["ttc_seconds"] == 15.0
    assert "chorus_lift" not in out["drop_features"]
