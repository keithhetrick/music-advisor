#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/ma_audio_features.py"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools.audio.ma_audio_features import main, select_tempo_with_folding

__all__ = ["main", "select_tempo_with_folding"]

if __name__ == "__main__":
    raise SystemExit(main())
