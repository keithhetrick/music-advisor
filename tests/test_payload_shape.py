from ma_audio_engine.always_present import coerce_payload_shape

def test_ttc_block_present():
    raw = {"audio_axes": [0.5]*6, "sr": 44100}  # no TTC given
    out = coerce_payload_shape(raw)
    assert "TTC" in out
    for k in ("seconds", "confidence", "lift_db", "dropped", "source"):
        assert k in out["TTC"]

def test_axes_len_6():
    raw = {"audio_axes": [0.1, 0.2, 0.3], "sr": 44100}
    out = coerce_payload_shape(raw)
    assert len(out["audio_axes"]) == 6
    assert out["audio_axes"][:3] == [0.1, 0.2, 0.3]
