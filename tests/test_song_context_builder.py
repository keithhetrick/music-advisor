from ma_host.song_context import build_song_context
from ma_lyrics_engine.bundle import build_bundle


def test_song_context_builder_with_bundles():
    audio_bundle = {"hci_score": 0.8, "axes": {"energy": 0.7}}
    bridge = {
        "count": 1,
        "items": [
            {
                "song_id": "wip1",
                "title": "Title",
                "artist": "Artist",
                "year": 2024,
                "lyric_confidence_index": {
                    "score": 0.7,
                    "raw": 0.6,
                    "calibration_profile": "lci_us_pop_v1",
                    "axes": {"structure_fit": 0.5},
                    "overlay": {"axes_z": {}, "lci_score_z": None},
                },
                "ttc_profile": {"ttc_confidence": "low"},
            }
        ],
    }
    neighbors = {"items": []}
    lyric_bundle = build_bundle(bridge, neighbors)
    meta = {"song_id": "wip1", "title": "Title", "artist": "Artist", "year": 2024}
    ctx = build_song_context(meta=meta, audio_bundle=audio_bundle, lyric_bundle=lyric_bundle)
    assert ctx["meta"]["song_id"] == "wip1"
    assert ctx["audio"]["hci_score"] == 0.8
    assert ctx["lyrics"]["lci"]["score"] == 0.7
