#!/usr/bin/env python3
"""Compatibility shim: routes to tools/calibration/make_calibration_snapshot.py"""
from tools.calibration.make_calibration_snapshot import main


if __name__ == "__main__":
    raise SystemExit(main())
