from pathlib import Path

from ma_lyrics_engine.lci_overlay import overlay_lci, find_lane


def test_overlay_computation():
    norms = {
        "profile": "lci_us_pop_v1",
        "lanes": [
            {
                "tier": 1,
                "era_bucket": "2015_2024",
                "axes_mean": {"structure_fit": 0.5, "prosody_ttc_fit": 0.5, "rhyme_texture_fit": 0.5, "diction_style_fit": 0.5, "pov_fit": 0.5, "theme_fit": 0.5},
                "axes_std": {"structure_fit": 0.1, "prosody_ttc_fit": 0.1, "rhyme_texture_fit": 0.1, "diction_style_fit": 0.1, "pov_fit": 0.1, "theme_fit": 0.1},
                "lci_score_mean": 0.6,
                "lci_score_std": 0.1,
                "ttc_seconds_mean": 30.0,
                "ttc_seconds_std": 5.0,
            }
        ],
    }
    lane = find_lane(norms, 1, "2015_2024", "lci_us_pop_v1")
    overlay = overlay_lci(
        song_axes={"structure_fit": 0.6, "prosody_ttc_fit": 0.5, "rhyme_texture_fit": 0.5, "diction_style_fit": 0.5, "pov_fit": 0.4, "theme_fit": 0.6},
        lci_score=0.7,
        ttc_seconds=35.0,
        lane_norms=lane,
    )
    assert round(overlay["axes_z"]["structure_fit"], 2) == 1.0
    assert round(overlay["lci_score_z"], 2) == 1.0
    assert round(overlay["ttc_seconds_z"], 2) == 1.0
