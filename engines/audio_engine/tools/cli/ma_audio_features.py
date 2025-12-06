#!/usr/bin/env python3
"""
Compatibility shim: routes to tools/audio/ma_audio_features.py
Kept for legacy imports (tools.cli.*) and Automator defaults.
"""
from tools.audio.ma_audio_features import main


if __name__ == "__main__":
    raise SystemExit(main())
