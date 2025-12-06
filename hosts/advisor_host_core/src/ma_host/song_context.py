"""
Host-facing song_context builder combining audio and lyric bundles.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def build_song_context(
    *,
    meta: Dict[str, Any],
    audio_bundle: Optional[Dict[str, Any]] = None,
    lyric_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a unified song_context dict for the Music Advisor client.

    meta: basic metadata (song_id, title, artist, year).
    audio_bundle: existing audio/HCI bundle (if available).
    lyric_bundle: lyric WIP bundle from ma_lyric_engine.bundle.
    """
    return {
        "meta": {
            "song_id": meta.get("song_id"),
            "title": meta.get("title"),
            "artist": meta.get("artist"),
            "year": meta.get("year"),
        },
        "audio": audio_bundle,
        "lyrics": lyric_bundle,
    }
