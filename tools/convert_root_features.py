#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/convert_root_features.py"""
from tools.audio.convert_root_features import main


if __name__ == "__main__":
    raise SystemExit(main())
