#!/usr/bin/env python3
"""
Diagnostics exporter CLI.

Usage:
  python -m advisor_host.cli.diagnostics_cli --log PATH --user-id USER --app-version VERSION [--out file]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from advisor_host.diagnostics.diagnostics import gather_diagnostics


def main() -> None:
    ap = argparse.ArgumentParser(description="Export redacted diagnostics bundle")
    ap.add_argument("--log", required=True, help="Path to host log (JSONL)")
    ap.add_argument("--user-id", required=True, help="User identifier (hashed before export)")
    ap.add_argument("--app-version", required=True, help="App version/build")
    ap.add_argument("--out", help="Output file; defaults to stdout if omitted")
    args = ap.parse_args()

    bundle = gather_diagnostics(Path(args.log), args.user_id, args.app_version)
    out_text = json.dumps(bundle, indent=2)
    if args.out:
        Path(args.out).write_text(out_text, encoding="utf-8")
        print(f"[diagnostics] wrote bundle -> {args.out}")
    else:
        print(out_text)


if __name__ == "__main__":
    main()
