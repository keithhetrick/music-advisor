#!/usr/bin/env python3
"""Compatibility shim: routes to tools/calibration/calibration_validator.py"""
from tools.calibration.calibration_validator import main


if __name__ == "__main__":
    raise SystemExit(main())
