#!/usr/bin/env python3
"""
Compatibility shim: routes to tools/calibration/backfill_features_meta.py
"""
from tools.calibration.backfill_features_meta import main

if __name__ == "__main__":
    raise SystemExit(main())
