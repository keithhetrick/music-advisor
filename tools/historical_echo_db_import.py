#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/historical_echo_db_import.py"""
from tools.audio.historical_echo_db_import import main


if __name__ == "__main__":
    raise SystemExit(main())
