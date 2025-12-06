#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/normalize_to_lufs.py"""
from tools.audio.normalize_to_lufs import main


if __name__ == "__main__":
    raise SystemExit(main())
