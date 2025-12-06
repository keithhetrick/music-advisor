"""
spine_slug.py

Shared slug helpers for Historical Spine.

Canonicalized from Tier 1 matching logic so Tier 2 joins/slugs stay consistent.
- Lowercase
- Drop bracketed parts (parentheses/brackets)
- Strip punctuation to spaces
- Collapse whitespace
- Build slug as "{artist_norm}__{title_norm}" (artist first for stability)
"""
from __future__ import annotations

import re
from typing import Tuple

_PARENS_RE = re.compile(r"\([^)]*\)|\[[^]]*\)")
_PUNCT_RE = re.compile(r"[^a-z0-9]+")


def normalize_spine_text(s: str) -> str:
    """Normalize title/artist for spine slugging.

    Mirrors Tier 1 backfill matching: lowercase, drop bracketed bits, remove punctuation,
    collapse whitespace.
    """
    s = (s or "").strip().lower()
    s = _PARENS_RE.sub(" ", s)
    s = _PUNCT_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def make_spine_slug(title: str, artist: str) -> str:
    """Return canonical spine slug used across Tier 1 & Tier 2."""
    return f"{normalize_spine_text(artist)}__{normalize_spine_text(title)}"


def make_year_slug_key(year: int, title: str, artist: str) -> Tuple[int, str]:
    """Convenience key for maps keyed by (year, slug)."""
    return int(year), make_spine_slug(title, artist)
