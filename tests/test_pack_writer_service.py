from tools.pack_writer import build_pack, build_client_helper_payload


def test_build_pack_minimal():
    merged = {
        "source_audio": "song.wav",
        "tempo_bpm": 120,
        "duration_sec": 180,
        "key": "C",
        "mode": "major",
        "loudness_LUFS": -10.0,
    }
    pack = build_pack(merged, audio_name="song", anchor="core")
    assert pack["audio_name"] == "song"
    assert pack["features"]["tempo_bpm"] == 120
    assert pack["features_full"]["loudness_lufs"] == -10.0
    client_helper = build_client_helper_payload(pack)
    assert client_helper["inputs"]["paths"]["source_audio"] == "song.wav"
