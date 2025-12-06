# Tests/test_ttc_synth_and_gate.py
from __future__ import annotations
from music_advisor.host.policy import Policy
from ma_hf_audiotools.Segmentation import SegmentationResult, apply_ttc_gate_and_lift
from Pipeline.ttc_synth import TTCInputs, synthesize_ttc_confidence

def test_ttc_synth_audio_tier():
    s = synthesize_ttc_confidence(TTCInputs(ttc_real=12.0))
    assert s["ttc_seconds"] == 12.0
    assert s["ttc_confidence"] == 0.80
    assert s["source"] == "audio"

def test_ttc_synth_lyrics_tier():
    s = synthesize_ttc_confidence(TTCInputs(ttc_lyrics=14.0))
    assert s["ttc_seconds"] == 14.0
    assert s["ttc_confidence"] == 0.50
    assert s["source"] == "lyrics"

def test_ttc_gate_respects_policy():
    # confidence below gate -> TTC None and chorus_lift dropped
    seg = SegmentationResult(ttc_seconds=15.0, ttc_confidence=0.55, verse_span=(10.0, 16.0), chorus_span=(30.0, 36.0))
    out = apply_ttc_gate_and_lift([0.0]*44100, 44100, seg, Policy(ttc_conf_gate=0.60))
    assert out["ttc_seconds"] is None
    assert "chorus_lift" in out["drop_features"]
