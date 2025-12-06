#!/usr/bin/env python3
"""
Compatibility shim: routes to tools/audio/tempo_sidecar_runner.py
"""
from tools.audio.tempo_sidecar_runner import main


if __name__ == "__main__":
    raise SystemExit(main())
