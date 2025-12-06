from tools.equilibrium_merge import merge_features


def test_merge_features_prefers_internal_and_fills_external():
    internal = {
        "source_audio": "song.wav",
        "duration_sec": 123,
        "tempo_bpm": 110,
        "key": "C",
        "mode": "major",
        "loudness_LUFS": -9.5,
        "energy": 0.7,
    }
    external = {"energy": 0.8, "danceability": 0.6, "valence": 0.5}
    merged = merge_features(internal, external)
    assert merged["tempo_bpm"] == 110
    assert merged["energy"] == 0.8  # external overrides
    assert merged["danceability"] == 0.6
    assert merged["valence"] == 0.5
