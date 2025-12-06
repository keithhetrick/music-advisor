#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/loudness_normalize_wav.py"""
from tools.audio.loudness_normalize_wav import main


if __name__ == "__main__":
    raise SystemExit(main())
