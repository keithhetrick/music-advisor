#!/usr/bin/env python3
"""
Shim to run the helper CLI from its new home (tools/ma_helper).
"""
from ma_helper.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
