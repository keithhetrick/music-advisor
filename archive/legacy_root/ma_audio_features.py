#!/usr/bin/env python3
"""
Shim: forward to ma_audio_engine.tools.ma_audio_features.
"""
from ma_audio_engine.tools.ma_audio_features import main

if __name__ == "__main__":
    raise SystemExit(main())
