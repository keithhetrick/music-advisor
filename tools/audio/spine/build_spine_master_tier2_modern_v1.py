#!/usr/bin/env python3
"""
build_spine_master_tier2_modern_v1.py

Build Tier 2 master spine CSV (core + audio) for EchoTier_2_YearEnd_Top100_Modern.

Inputs:
  - Core metadata: data/spine/spine_core_tracks_tier2_modern_v1.csv
  - Audio features: data/spine/spine_audio_tier2_modern_v1_enriched.csv

Output:
  - data/spine/spine_master_tier2_modern_v1.csv

Tier 1 behavior and files remain untouched.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple

from shared.config.paths import get_spine_root

def read_indexed_csv(path: Path, key_field: str) -> Tuple[Dict[str, dict], List[str]]:
    if not path.exists():
        raise SystemExit(f"[build_spine_master_tier2_modern_v1] Missing CSV: {path}")

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"[build_spine_master_tier2_modern_v1] Empty CSV or missing header: {path}")

        if key_field not in reader.fieldnames:
            raise SystemExit(
                f"[build_spine_master_tier2_modern_v1] Key field '{key_field}' not found in {path} "
                f"header: {reader.fieldnames}"
            )

        rows: Dict[str, dict] = {}
        for row in reader:
            key = (row.get(key_field) or "").strip()
            if not key:
                continue
            rows[key] = row

        return rows, list(reader.fieldnames)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Tier 2 master spine CSV (core + audio).")
    parser.add_argument(
        "--core",
        default=str(get_spine_root() / "spine_core_tracks_tier2_modern_v1.csv"),
        help="Tier 2 core metadata CSV.",
    )
    parser.add_argument(
        "--audio",
        default=str(get_spine_root() / "spine_audio_tier2_modern_v1_enriched.csv"),
        help="Tier 2 enriched audio CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(get_spine_root() / "spine_master_tier2_modern_v1.csv"),
        help="Output master CSV path.",
    )

    args = parser.parse_args()

    core_path = Path(args.core)
    audio_path = Path(args.audio)
    out_path = Path(args.out)

    print(f"[build_spine_master_tier2_modern_v1] Loading core spine from: {core_path}")
    core_by_id, core_fields = read_indexed_csv(core_path, "spine_track_id")

    print(f"[build_spine_master_tier2_modern_v1] Loading audio spine from: {audio_path}")
    audio_by_id, audio_fields_all = read_indexed_csv(audio_path, "spine_track_id")

    PROTECTED_FIELDS = {
        "spine_track_id",
        "year",
        "chart",
        "year_end_rank",
        "echo_tier",
        "artist",
        "title",
        "slug",
        "tier_label",
        "source_chart",
        "billboard_source",
    }

    audio_fields: List[str] = [f for f in audio_fields_all if f not in PROTECTED_FIELDS]

    fieldnames: List[str] = list(core_fields)
    for f in audio_fields:
        if f not in fieldnames:
            fieldnames.append(f)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[build_spine_master_tier2_modern_v1] Writing master spine to: {out_path}")
    audio_match_count = 0

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for spine_id, core_row in core_by_id.items():
            row = {fn: core_row.get(fn, "") for fn in core_fields}
            audio_row = audio_by_id.get(spine_id)
            if audio_row:
                audio_match_count += 1
                for fn in audio_fields:
                    val = audio_row.get(fn, "")
                    if val not in ("", None):
                        row[fn] = val
            writer.writerow(row)

    total = len(core_by_id)
    print(
        f"[build_spine_master_tier2_modern_v1] Done. "
        f"Wrote {total} rows. Audio matched for {audio_match_count} / {total} spine tracks."
    )


if __name__ == "__main__":
    main()
