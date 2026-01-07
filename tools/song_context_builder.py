#!/usr/bin/env python3
"""Shim to engine CLI implementation (ma_audio_engine.cli.song_context_builder)."""
from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.cli.song_context_builder import main  # noqa: E402

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())
