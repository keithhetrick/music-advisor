"""Compatibility wrapper to relocated lyrics engine."""
from ma_lyrics_engine.lci import (
    axis_score,
    build_calibration,
    clamp01,
    compute_axis_raws,
    compute_lci_for_song,
    fetch_features_row,
    iter_song_ids_for_scoring,
    load_calibration,
    score_axes_to_lci,
    upsert_features_song_lci,
    weighted_axis_mean,
)

__all__ = [
    "axis_score",
    "build_calibration",
    "clamp01",
    "compute_axis_raws",
    "compute_lci_for_song",
    "fetch_features_row",
    "iter_song_ids_for_scoring",
    "load_calibration",
    "score_axes_to_lci",
    "upsert_features_song_lci",
    "weighted_axis_mean",
]
