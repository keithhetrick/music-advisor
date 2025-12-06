#!/usr/bin/env python3
"""
Compatibility shim: exposes FeatureCache (and a minimal CLI) while delegating
the real implementation to tools/audio/cache_utils.py. This keeps legacy
imports like ``from tools.cache_utils import FeatureCache`` working.
"""
from __future__ import annotations

import argparse

from tools.audio.cache_utils import FeatureCache


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal cache shim")
    parser.add_argument("--gc", action="store_true", help="Run cache garbage collection")
    parser.add_argument("--cache-dir", default=None, help="Cache directory to target")
    args = parser.parse_args()

    cache = FeatureCache(args.cache_dir)
    if args.gc:
        stats = cache.gc()
        print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
