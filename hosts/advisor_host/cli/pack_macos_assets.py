#!/usr/bin/env python3
"""
Gather minimal assets/configs for macOS packaging (offline-first bundle).

Copies into a target directory (default: build/macos_bundle_assets):
- config/host_profiles.yml
- config/intents.yml
- schema/reply_schema.json
- tutorials content (tutorials.py kept as code)
- a baseline norms snapshot if present (optional path)

Usage:
  python -m advisor_host.cli.pack_macos_assets [--out build/macos_bundle_assets] [--baseline-norms path]
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser(description="Pack minimal assets for macOS bundle")
    ap.add_argument("--out", default="build/macos_bundle_assets", help="Output directory")
    ap.add_argument("--baseline-norms", help="Optional baseline norms JSON to include")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Core configs
    copy_file(ROOT / "config" / "host_profiles.yml", out_dir / "config" / "host_profiles.yml")
    copy_file(ROOT / "config" / "intents.yml", out_dir / "config" / "intents.yml")
    copy_file(ROOT / "schema" / "reply_schema.json", out_dir / "schema" / "reply_schema.json")

    # Optional baseline norms
    if args.baseline_norms:
        src = Path(args.baseline_norms)
        if src.exists():
            copy_file(src, out_dir / "data" / src.name)

    print(f"[pack_macos_assets] wrote assets to {out_dir}")


if __name__ == "__main__":
    main()
