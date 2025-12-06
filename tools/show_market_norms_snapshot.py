#!/usr/bin/env python3
"""
Inspect a market_norms snapshot JSON and report key metadata.

Usage:
  python tools/show_market_norms_snapshot.py --snapshot <DATA_ROOT>/market_norms/US_BillboardTop100_2025-01.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Show market_norms snapshot metadata.")
    ap.add_argument("--snapshot", required=True, help="Path to snapshot JSON.")
    args = ap.parse_args()

    snap = json.loads(Path(args.snapshot).read_text())
    meta = {k: snap.get(k) for k in ("region", "tier", "version", "last_refreshed_at")}
    print(f"Snapshot: {args.snapshot}")
    print(f"Meta: {meta}")
    if "tempo_bpm" in snap:
        print(f"tempo_bpm: {snap['tempo_bpm']}")
    if "duration_sec" in snap:
        print(f"duration_sec: {snap['duration_sec']}")


if __name__ == "__main__":
    main()
