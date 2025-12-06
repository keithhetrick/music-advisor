#!/usr/bin/env python3
"""
Build a market_norms_snapshot JSON from a CSV of audio features.

Expected CSV columns (at least):
- tempo_bpm
- duration_sec or duration_ms
- loudness_LUFS
- energy
- danceability
- valence

Usage:
  python scripts/build_market_norms_snapshot.py --csv tracks.csv --region US --tier StreamingTop200 --version 2025-01 --out <DATA_ROOT>/market_norms

Notes:
- This is a file-based builder intended for monthly offline runs.
- Upstream chart fetch -> CSV (with features) should precede this step.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

FEATURE_KEYS = ["tempo_bpm", "duration_sec", "loudness_LUFS", "energy", "danceability", "valence"]


def load_rows(csv_path: Path) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            row: Dict[str, float] = {}
            # normalize duration_ms -> duration_sec if needed
            if "duration_ms" in r and r.get("duration_sec") is None:
                try:
                    r["duration_sec"] = float(r["duration_ms"]) / 1000.0
                except Exception:
                    pass
            for key in FEATURE_KEYS:
                val = r.get(key)
                if val is None or val == "":
                    continue
                try:
                    row[key] = float(val)
                except Exception:
                    continue
            if row:
                rows.append(row)
    return rows


def compute_stats(values: List[float]) -> Dict[str, float]:
    arr = np.array(values, dtype=float)
    return {
        "p10": float(np.percentile(arr, 10)),
        "p25": float(np.percentile(arr, 25)),
        "p50": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
        "mean": float(np.mean(arr)),
    }


def build_snapshot(rows: List[Dict[str, float]], region: str, tier: str, version: str, last_refreshed_at: Optional[str]) -> Dict[str, any]:
    snapshot = {
        "region": region,
        "tier": tier,
        "version": version,
        "last_refreshed_at": last_refreshed_at,
    }
    axes: Dict[str, Dict[str, float]] = {}
    for key in FEATURE_KEYS:
        vals = [r[key] for r in rows if key in r]
        if vals:
            snapshot[key] = compute_stats(vals)
            # For simplicity, mirror feature stats into axes if the axis name matches
            axis_name = None
            if key == "tempo_bpm":
                axis_name = "TempoFit"
            elif key == "duration_sec":
                axis_name = "RuntimeFit"
            elif key == "loudness_LUFS":
                axis_name = "LoudnessFit"
            elif key == "energy":
                axis_name = "Energy"
            elif key == "danceability":
                axis_name = "Danceability"
            elif key == "valence":
                axis_name = "Valence"
            if axis_name:
                axes[axis_name] = snapshot[key]
    if axes:
        snapshot["axes"] = axes
    return snapshot


def main() -> None:
    ap = argparse.ArgumentParser(description="Build market_norms_snapshot JSON from CSV features.")
    ap.add_argument("--csv", required=True, help="Input CSV with feature columns.")
    ap.add_argument("--region", required=True)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--version", required=True, help="e.g., 2025-01 or 2024-YE")
    ap.add_argument("--last-refreshed-at", dest="last_refreshed_at", default=None)
    ap.add_argument("--out", required=True, help="Output directory (e.g., <DATA_ROOT>/market_norms)")
    args = ap.parse_args()

    rows = load_rows(Path(args.csv))
    if not rows:
        raise SystemExit("No usable rows found in CSV.")
    snapshot = build_snapshot(rows, args.region, args.tier, args.version, args.last_refreshed_at)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.region}_{args.tier}_{args.version}.json"
    out_path.write_text(json.dumps(snapshot, indent=2))
    print(f"[market_norms] wrote snapshot -> {out_path}")


if __name__ == "__main__":
    main()
