#!/usr/bin/env python3
"""Compatibility shim: routes to tools/audio/validate_features_shape.py"""
from tools.audio.validate_features_shape import main


if __name__ == "__main__":
    raise SystemExit(main())
