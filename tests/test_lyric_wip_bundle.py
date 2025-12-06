import json

from ma_lyric_engine.bundle import build_bundle


def test_bundle_builder_shapes_output():
    bridge = {
        "count": 1,
        "items": [
            {
                "song_id": "wip1",
                "title": "Title",
                "artist": "Artist",
                "year": 2024,
                "tier": 1,
                "era_bucket": "2015_2024",
                "lyric_confidence_index": {
                    "score": 0.7,
                    "raw": 0.6,
                    "calibration_profile": "lci_us_pop_v1",
                    "axes": {"structure_fit": 0.5},
                    "overlay": {"lci_score_z": 0.5, "axes_z": {"structure_fit": 0.5}},
                },
                "ttc_profile": {"ttc_seconds_first_chorus": None, "ttc_confidence": "low"},
            }
        ],
    }
    neighbors = {"items": [{"song_id": "nbr1", "title": "N1", "artist": "A1", "year": 2010, "similarity": 0.9}]}
    bundle = build_bundle(bridge, neighbors)
    assert bundle["song_id"] == "wip1"
    assert bundle["lci"]["percentiles"]["structure_fit"] is not None
    assert bundle["ttc"]["ttc_confidence"] == "low"
    assert bundle["neighbors"][0]["song_id"] == "nbr1"
