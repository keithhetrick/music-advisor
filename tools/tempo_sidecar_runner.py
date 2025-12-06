#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/tempo_sidecar_runner.py"""
from pathlib import Path
import sys

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools.audio.tempo_sidecar_runner import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
