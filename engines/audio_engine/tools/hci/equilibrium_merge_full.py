#!/usr/bin/env python3
"""
Compatibility shim: routes to tools/cli/equilibrium_merge_full.py
"""
from tools.cli.equilibrium_merge_full import main

if __name__ == "__main__":
    raise SystemExit(main())
