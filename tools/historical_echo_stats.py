#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/historical_echo_stats.py"""
from tools.audio.historical_echo_stats import main


if __name__ == "__main__":
    raise SystemExit(main())
