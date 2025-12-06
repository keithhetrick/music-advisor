#!/usr/bin/env python3
"""Compatibility shim: routes to tools/calibration/calib_coverage.py"""
from tools.calibration.calib_coverage import main


if __name__ == "__main__":
    raise SystemExit(main())
