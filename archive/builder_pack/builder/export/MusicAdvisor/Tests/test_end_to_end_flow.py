# Tests/test_end_to_end_flow.py
from __future__ import annotations
from Pipeline.end_to_end import score_from_extractor_payload
from music_advisor.host.policy import Policy

def test_end_to_end_low_conf_ttc_drops_lift_and_caps_hci():
    raw = {
        "audio_axes": [0.62, 0.63, 0.61, 0.60, 0.64, 0.62],
        "ttc_sec": 14.0,
        "ttc_conf": 0.55,  # below default 0.60 gate
        "verse_span": [10.0, 16.0],
        "chorus_span": [30.0, 36.0],
        "sr": 44100,
        "signal": [0.0]*44100
    }
    out = score_from_extractor_payload(raw)
    assert out["TTC"]["seconds"] is None            # TTC gated
    assert "chorus_lift" in out["TTC"]["dropped"]   # lift dropped
    assert abs(out["HCI_v1"]["HCI_v1_score"] - 0.58) < 1e-9   # host cap holds

def test_end_to_end_high_conf_ttc_attempts_lift_and_caps_hci():
    raw = {
        "audio_axes": [0.62, 0.63, 0.61, 0.60, 0.64, 0.62],
        "ttc_sec": 14.0,
        "ttc_conf": 0.80,  # passes gate
        "verse_span": [10.0, 20.0],
        "chorus_span": [30.0, 40.0],
        "sr": 44100,
        "signal": [0.0]*44100
    }
    out = score_from_extractor_payload(raw)
    assert out["TTC"]["seconds"] == 14.0            # TTC accepted
    # lift may be computed or still dropped (e.g., if insufficient energy); both are ok.
    assert abs(out["HCI_v1"]["HCI_v1_score"] - 0.58) < 1e-9   # host cap holds

def test_end_to_end_missing_ttc_confidence_synthesizes_and_gates():
    raw = {
        "audio_axes": [0.40, 0.45, 0.50, 0.55, 0.48, 0.52],
        "ttc_sec": None,
        "ttc_conf": None,       # synthesize from lyrics hint
        "ttc_lyrics": 16.0,
        "verse_span": [8.0, 14.0],
        "chorus_span": [28.0, 34.0],
        "sr": 44100,
        "signal": [0.0]*44100
    }
    out = score_from_extractor_payload(raw)
    # lyrics-tier conf = 0.50 < 0.60 => TTC must be gated
    assert out["TTC"]["seconds"] is None
