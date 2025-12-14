#!/usr/bin/env python3
"""
Back-compat wrapper for the ma_helper CLI.

The canonical implementation lives in ma_helper/cli_app.py and is exposed via
console scripts (`ma`, `ma-helper`) or `python -m ma_helper`. This wrapper
remains for scripts that still call tools/ma_helper/cli.py directly.
"""
from __future__ import annotations

from ma_helper.cli_app import main


if __name__ == "__main__":
    raise SystemExit(main())
