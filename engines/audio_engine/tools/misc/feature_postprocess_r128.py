#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/feature_postprocess_r128.py"""
from tools.audio.feature_postprocess_r128 import main


if __name__ == "__main__":
    raise SystemExit(main())
