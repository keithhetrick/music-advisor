#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/historical_echo_backfill_tier3_audio.py"""
from tools.audio.historical_echo_backfill_tier3_audio import main


if __name__ == "__main__":
    raise SystemExit(main())
