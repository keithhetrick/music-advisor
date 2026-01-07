#!/usr/bin/env python3
"""Shim to engine CLI implementation (ma_lyrics_engine.cli.lyric_wip_pipeline)."""
from ma_lyrics_engine.cli.lyric_wip_pipeline import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())
