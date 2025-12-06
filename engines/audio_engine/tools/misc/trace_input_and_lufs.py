#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/trace_input_and_lufs.py"""
from tools.audio.trace_input_and_lufs import main


if __name__ == "__main__":
    raise SystemExit(main())
