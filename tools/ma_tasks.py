#!/usr/bin/env python3
"""
Legacy shim that delegates to tools/ma_orchestrator.py.

Existing Makefile/CI entrypoints call this file; keep it as a thin wrapper so
new users can use the richer orchestrator directly.
"""
from __future__ import annotations

import sys

import ma_orchestrator


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    # Preserve compatibility: `list` → `list-projects`.
    if args and args[0] == "list":
        args[0] = "list-projects"
    return ma_orchestrator.main(args)


if __name__ == "__main__":
    sys.exit(main())
