#!/usr/bin/env python3
"""
spine_coverage_report_v1.py

Coverage report for the Historical Echo Core Spine v1 ("Core 1600").
Defaults resolve via env (MA_SPINE_ROOT) and can be overridden via CLI.
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, Any, List

from ma_config.paths import get_spine_root


def load_csv_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Coverage report for Historical Echo Core Spine v1 (Core 1600)."
    )
    default_root = get_spine_root()
    parser.add_argument(
        "--core",
        default=str(default_root / "spine_core_tracks_v1.csv"),
        help="Path to core spine CSV.",
    )
    parser.add_argument(
        "--audio",
        default=str(default_root / "spine_audio_spotify_v1.csv"),
        help="Path to audio spine CSV.",
    )
    parser.add_argument(
        "--out-coverage",
        default=str(default_root / "spine_coverage_by_year_v1.csv"),
        help="Output CSV for coverage by year.",
    )
    parser.add_argument(
        "--out-unmatched",
        default=str(default_root / "spine_unmatched_core_v1.csv"),
        help="Output CSV listing core tracks with no audio match.",
    )

    args = parser.parse_args()
    core_path = Path(args.core).expanduser()
    audio_path = Path(args.audio).expanduser()
    out_cov_path = Path(args.out_coverage).expanduser()
    out_unmatched_path = Path(args.out_unmatched).expanduser()

    print(f"[INFO] Loading core spine from {core_path} ...")
    core_rows = load_csv_rows(core_path)
    print(f"[INFO] Loaded {len(core_rows)} core rows")

    print(f"[INFO] Loading audio spine from {audio_path} ...")
    audio_rows = load_csv_rows(audio_path)
    print(f"[INFO] Loaded {len(audio_rows)} audio rows")

    # Build set of spine_track_ids that have audio
    audio_ids = {r.get("spine_track_id") for r in audio_rows if r.get("spine_track_id")}
    print(f"[INFO] Unique spine_track_ids with audio: {len(audio_ids)}")

    # Coverage by year
    coverage_by_year = {}
    unmatched_rows: List[Dict[str, Any]] = []

    for r in core_rows:
        sid = r.get("spine_track_id")
        year_str = r.get("year")
        try:
            year = int(year_str) if year_str is not None else None
        except ValueError:
            year = None

        if year is None:
            # treat as bucket "unknown"
            year_key = "unknown"
        else:
            year_key = str(year)

        bucket = coverage_by_year.setdefault(
            year_key,
            {"year": year_key, "n_core": 0, "n_with_audio": 0},
        )
        bucket["n_core"] += 1

        if sid in audio_ids:
            bucket["n_with_audio"] += 1
        else:
            unmatched_rows.append(r)

    # Compute percentages
    for bucket in coverage_by_year.values():
        n_core = bucket["n_core"]
        n_with = bucket["n_with_audio"]
        pct = (n_with / n_core * 100.0) if n_core else 0.0
        bucket["pct_with_audio"] = round(pct, 1)

    # Write coverage by ye
