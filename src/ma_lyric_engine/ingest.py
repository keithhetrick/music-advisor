"""Compatibility wrapper to relocated lyrics engine."""
from ma_lyrics_engine.ingest import (
    ingest_billboard_spine,
    ingest_fallback_top100,
    ingest_hot100_lyrics_audio,
    ingest_kaggle_year_end,
    should_replace,
    upsert_lyrics,
    upsert_song,
)

__all__ = [
    "ingest_billboard_spine",
    "ingest_fallback_top100",
    "ingest_hot100_lyrics_audio",
    "ingest_kaggle_year_end",
    "should_replace",
    "upsert_lyrics",
    "upsert_song",
]
