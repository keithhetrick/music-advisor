#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/build_historical_echo_corpus.py"""
from tools.audio.build_historical_echo_corpus import main


if __name__ == "__main__":
    raise SystemExit(main())
