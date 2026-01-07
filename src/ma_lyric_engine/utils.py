"""Compatibility wrapper to relocated lyrics engine."""
from ma_lyrics_engine.utils import (
    clean_lyrics_text,
    count_syllables,
    normalize_text,
    rhyme_key,
    section_label_from_tag,
    sectionize,
    slugify_song,
    tokenize_words,
)

__all__ = [
    "clean_lyrics_text",
    "count_syllables",
    "normalize_text",
    "rhyme_key",
    "section_label_from_tag",
    "sectionize",
    "slugify_song",
    "tokenize_words",
]
