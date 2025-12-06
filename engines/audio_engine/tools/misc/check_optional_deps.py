#!/usr/bin/env python3
"""
Optional dependency check: report presence/versions of whisper/faster-whisper/pyloudnorm/audioread.
"""
from __future__ import annotations

import importlib

OPTIONAL = [
    "pyloudnorm",
    "whisper",
    "faster_whisper",
    "audioread",
]


def check() -> int:
    status = 0
    for mod in OPTIONAL:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "unknown")
            print(f"{mod}: present ({ver})")
        except Exception as exc:  # noqa: BLE001
            print(f"{mod}: missing ({exc})")
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(check())
