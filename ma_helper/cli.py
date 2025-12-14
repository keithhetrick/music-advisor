#!/usr/bin/env python3
"""
Canonical ma_helper CLI entrypoint.

Implementation lives in ma_helper/cli_app.py; tools/ma_helper/cli.py is a thin
wrapper for back-compat.
"""
from __future__ import annotations

from .cli_app import main  # re-export


if __name__ == "__main__":
    raise SystemExit(main())
