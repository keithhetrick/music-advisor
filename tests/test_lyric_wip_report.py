from pathlib import Path

from tools.lyric_wip_report import render_report


def test_render_report_outputs_expected_sections(tmp_path):
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
                    "axes": {
                        "structure_fit": 0.5,
                        "prosody_ttc_fit": 0.6,
                        "rhyme_texture_fit": 0.7,
                        "diction_style_fit": 0.8,
                        "pov_fit": 0.9,
                        "theme_fit": 0.4,
                    },
                    "raw": 0.6,
                    "score": 0.7,
                    "calibration_profile": "lci_us_pop_v1",
                },
                "ttc_profile": {
                    "ttc_seconds_first_chorus": None,
                    "ttc_bar_position_first_chorus": None,
                    "estimation_method": "ttc_rule_based_v1",
                    "profile": "ttc_us_pop_v1",
                },
            }
        ],
    }
    neighbors = {
        "song_id": "wip1",
        "count": 2,
        "items": [
            {"song_id": "wip1", "title": "Self", "artist": "Self", "year": 2024, "similarity": 1.0},
            {"song_id": "nbr1", "title": "N1", "artist": "A1", "year": 2010, "similarity": 0.9, "tier": 1, "era_bucket": "2015_2024"},
            {"song_id": "nbr2", "title": "N2", "artist": "A2", "year": 2012, "similarity": 0.8},
        ],
    }
    norms = {
        "profile": "lci_us_pop_v1",
        "lanes": [
            {
                "tier": 1,
                "era_bucket": "2015_2024",
                "axes_mean": {k: 0.4 for k in ["structure_fit", "prosody_ttc_fit", "rhyme_texture_fit", "diction_style_fit", "pov_fit", "theme_fit"]},
                "axes_std": {k: 0.1 for k in ["structure_fit", "prosody_ttc_fit", "rhyme_texture_fit", "diction_style_fit", "pov_fit", "theme_fit"]},
                "lci_score_mean": 0.6,
                "lci_score_std": 0.1,
                "ttc_seconds_mean": 30.0,
                "ttc_seconds_std": 5.0,
            }
        ],
    }
    report = render_report(bridge, neighbors, top_k=2, norms=norms, include_self=False)
    assert "LCI" in report
    assert "structure_fit" in report
    assert "ttc_rule_based_v1" in report
    assert "N1" in report
    assert "p ~" in report  # percentiles
    assert "tier=1" in report
    assert "Self" not in report


def test_report_handles_missing_lane_norms_and_shows_neighbors():
    bridge = {
        "count": 1,
        "items": [
            {
                "song_id": "wip1",
                "title": "Title",
                "artist": "Artist",
                "year": 2024,
                "tier": None,
                "era_bucket": "unknown_era",
                "lyric_confidence_index": {"axes": {"structure_fit": 0.5}, "score": 0.7, "raw": 0.6, "calibration_profile": "lci_us_pop_v1"},
                "ttc_profile": {},
            }
        ],
    }
    neighbors = {
        "song_id": "wip1",
        "count": 1,
        "items": [
            {"song_id": "nbr1", "title": "N1", "artist": "A1", "year": 2010, "similarity": 0.9, "tier": 1, "era_bucket": "2015_2024"},
        ],
    }
    norms = {"profile": "lci_us_pop_v1", "lanes": [{"tier": 1, "era_bucket": "2015_2024", "axes_mean": {"structure_fit": 0.4}, "axes_std": {"structure_fit": 0.1}, "lci_score_mean": 0.6, "lci_score_std": 0.1, "ttc_seconds_mean": 30.0, "ttc_seconds_std": 5.0}]}
    report = render_report(bridge, neighbors, top_k=5, norms=norms, lane_era_filter="missing_era")
    assert "Overlay: no norms found" in report
    assert "N1" in report


def test_report_dedupes_neighbors_by_title_artist_year():
    bridge = {
        "count": 1,
        "items": [
            {
                "song_id": "wip1",
                "title": "Title",
                "artist": "Artist",
                "year": 2024,
                "lyric_confidence_index": {"axes": {}, "score": 0.7, "raw": 0.6, "calibration_profile": "lci_us_pop_v1"},
                "ttc_profile": {},
            }
        ],
    }
    neighbors = {
        "song_id": "wip1",
        "count": 3,
        "items": [
            {"song_id": "nbr1", "title": "Same", "artist": "Artist", "year": 2000, "similarity": 0.9},
            {"song_id": "nbr2", "title": "Same", "artist": "Artist", "year": 2000, "similarity": 0.8},
            {"song_id": "nbr3", "title": "Different", "artist": "Other", "year": 2001, "similarity": 0.7},
        ],
    }
    report = render_report(bridge, neighbors, top_k=5, norms=None, include_self=False)
    assert report.count("Same") == 1
    assert "Different" in report
