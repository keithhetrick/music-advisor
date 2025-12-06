#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/pack_postprocess_calibrate.py"""
from tools.audio.pack_postprocess_calibrate import main


if __name__ == "__main__":
    raise SystemExit(main())
