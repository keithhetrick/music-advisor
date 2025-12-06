#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/loudnorm_exact.py"""
from tools.audio.loudnorm_exact import main


if __name__ == "__main__":
    raise SystemExit(main())
