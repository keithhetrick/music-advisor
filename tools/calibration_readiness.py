#!/usr/bin/env python3
"""Compatibility shim: routes to calibration readiness CLI (tools/calibration/calibration_readiness.py)."""
from tools.calibration.calibration_readiness import main

if __name__ == "__main__":
    raise SystemExit(main())
