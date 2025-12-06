#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/sanitize_filenames.py"""
from tools.audio.sanitize_filenames import main


if __name__ == "__main__":
    raise SystemExit(main())
