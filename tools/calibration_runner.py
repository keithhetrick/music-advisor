#!/usr/bin/env python3
"""Compatibility shim: routes to tools/calibration/calibration_runner.py"""
from tools.calibration.calibration_runner import main


if __name__ == "__main__":
    raise SystemExit(main())
