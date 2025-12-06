sample_payload = {
    "region": "US",
    "profile": "Pop",
    "audio_name": "example_track",
    "features_full": {
        "tempo_bpm": 140.0,
        "duration_sec": 285,
        "loudness_LUFS": -13.5,
        "energy": 0.72,
        "danceability": 0.61,
        "valence": 0.45,
    },
    "audio_axes": {
        "TempoFit": 0.35,
        "RuntimeFit": 0.30,
        "LoudnessFit": 0.40,
        "Energy": 0.70,
        "Danceability": 0.58,
        "Valence": 0.40,
    },
    "HCI_v1_final_score": 0.55,
    "historical_echo_v1": {
        "primary_decade": "2015–2024",
        "primary_decade_neighbor_count": 4,
        "top_neighbor": {"year": 2018, "artist": "Example Artist", "title": "Example Hit", "distance": 0.52},
    },
}

sample_market_norms = {
    "region": "US",
    "tier": "Tier1_Hot100_Top40",
    "version": "2024-YE",
    "last_refreshed_at": "2025-01-15T00:00:00Z",
    "tempo_bpm": {"p10": 80, "p25": 90, "p50": 102, "p75": 120, "p90": 130},
    "duration_sec": {"p10": 150, "p25": 170, "p50": 200, "p75": 230, "p90": 260},
    "loudness_LUFS": {"p10": -13.0, "p25": -11.5, "p50": -9.0, "p75": -8.0, "p90": -7.0},
    "energy": {"p10": 0.4, "p25": 0.5, "p50": 0.65, "p75": 0.8, "p90": 0.9},
    "danceability": {"p10": 0.4, "p25": 0.5, "p50": 0.65, "p75": 0.8, "p90": 0.9},
    "valence": {"p10": 0.3, "p25": 0.4, "p50": 0.6, "p75": 0.75, "p90": 0.85},
    "axes": {
        "TempoFit": {"p10": 0.4, "p25": 0.5, "p50": 0.7, "p75": 0.85, "p90": 0.95},
        "RuntimeFit": {"p10": 0.4, "p25": 0.5, "p50": 0.7, "p75": 0.85, "p90": 0.95},
        "LoudnessFit": {"p10": 0.4, "p25": 0.5, "p50": 0.7, "p75": 0.85, "p90": 0.95},
        "Energy": {"p10": 0.4, "p25": 0.5, "p50": 0.7, "p75": 0.85, "p90": 0.95},
        "Danceability": {"p10": 0.4, "p25": 0.5, "p50": 0.7, "p75": 0.85, "p90": 0.95},
        "Valence": {"p10": 0.4, "p25": 0.5, "p50": 0.7, "p75": 0.85, "p90": 0.95},
    },
}
