#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/ma_audio_features.py"""
from pathlib import Path
from ma_audio_engine.adapters.bootstrap import ensure_repo_root
import sys

ensure_repo_root()

from tools.audio.ma_audio_features import main, select_tempo_with_folding

__all__ = ["main", "select_tempo_with_folding"]

if __name__ == "__main__":
    raise SystemExit(main())
