"""Compatibility wrapper to relocated lyrics engine."""
from ma_lyrics_engine.features import (
    compute_features_for_song,
    load_concreteness_lexicon,
    load_vader,
    sentiment_scores,
    sonic_texture_scores,
    theme_scores,
    write_section_and_line_tables,
    write_song_features,
)

__all__ = [
    "compute_features_for_song",
    "load_concreteness_lexicon",
    "load_vader",
    "sentiment_scores",
    "sonic_texture_scores",
    "theme_scores",
    "write_section_and_line_tables",
    "write_song_features",
]
