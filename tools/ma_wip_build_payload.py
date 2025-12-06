#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/ma_wip_build_payload.py"""
from tools.audio.ma_wip_build_payload import main


if __name__ == "__main__":
    raise SystemExit(main())
