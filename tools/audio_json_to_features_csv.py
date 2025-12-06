#!/usr/bin/env python3
"""
Convert engine /audio JSON outputs (e.g., *.merged.json) into a CSV suitable
for market_norms_snapshot builder.

Inputs:
- A glob of JSON files (defaults to **/*.merged.json).
- Optional chart CSV (e.g., hot100_top40_2025_11.csv) to carry title/artist/chart_date/rank.

Output CSV columns:
title, artist, chart_date, rank, tempo_bpm, duration_sec, loudness_LUFS, energy, danceability, valence

Usage:
  PYTHONPATH=. python tools/audio_json_to_features_csv.py \
    --json-glob "features_output/**/*.merged.json" \
    --chart-csv <DATA_ROOT>/market_norms/raw/hot100_top40_2025_11.csv \
    --out <DATA_ROOT>/market_norms/raw/hot100_top40_2025_11_features.csv
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


def normalize_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load_chart_lookup(chart_csv: Optional[Path]) -> Dict[str, Dict[str, str]]:
    if not chart_csv:
        return {}
    df = pd.read_csv(chart_csv)
    lookup: Dict[str, Dict[str, str]] = {}
    for _, row in df.iterrows():
        title = str(row.get("title", "") or "")
        artist = str(row.get("artist", "") or "")
        key = normalize_token(title)
        lookup[key] = {
            "title": title,
            "artist": artist,
            "chart_date": str(row.get("chart_date", "") or ""),
            "rank": str(row.get("rank", "") or ""),
        }
    return lookup


def extract_features(path: Path) -> Optional[Dict[str, float]]:
    with path.open() as f:
        data = json.load(f)
    # Expecting merged-style fields
    required = ["tempo_bpm", "duration_sec", "loudness_LUFS", "energy", "danceability", "valence"]
    if not all(k in data for k in required):
        return None
    return {
        "tempo_bpm": data.get("tempo_bpm"),
        "duration_sec": data.get("duration_sec"),
        "loudness_LUFS": data.get("loudness_LUFS"),
        "energy": data.get("energy"),
        "danceability": data.get("danceability"),
        "valence": data.get("valence"),
        "source_audio": str(data.get("source_audio", "")),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert /audio JSON outputs to features CSV for norms builder.")
    ap.add_argument("--json-glob", required=True, help='Glob for engine outputs, e.g. "features_output/**/*.merged.json"')
    ap.add_argument("--chart-csv", help="Optional chart CSV (title,artist,chart_date,rank).")
    ap.add_argument("--out", required=True, help="Output CSV path.")
    args = ap.parse_args()

    chart_lookup = load_chart_lookup(Path(args.chart_csv)) if args.chart_csv else {}

    rows: List[Dict[str, str]] = []
    for path_str in glob.glob(args.json_glob, recursive=True):
        path = Path(path_str)
        feats = extract_features(path)
        if not feats:
            continue
        base = Path(feats["source_audio"]).stem or path.stem
        key = normalize_token(base)
        meta = chart_lookup.get(key, {})
        rows.append(
            {
                "title": meta.get("title", base),
                "artist": meta.get("artist", ""),
                "chart_date": meta.get("chart_date", ""),
                "rank": meta.get("rank", ""),
                "tempo_bpm": feats["tempo_bpm"],
                "duration_sec": feats["duration_sec"],
                "loudness_LUFS": feats["loudness_LUFS"],
                "energy": feats["energy"],
                "danceability": feats["danceability"],
                "valence": feats["valence"],
            }
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"[audio_json_to_features_csv] wrote {len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    main()
