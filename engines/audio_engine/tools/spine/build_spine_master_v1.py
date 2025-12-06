#!/usr/bin/env python3
"""
Build Tier 1 master spine CSV by merging:
- Core Billboard Year-End Top 40 metadata (canonical)
- Enriched audio features (base + backfills)

Canonical metadata source:
    spine_core_tracks_v1.csv (default via MA_SPINE_ROOT)

Audio source:
    spine_audio_spotify_v1_enriched.csv (default via MA_SPINE_ROOT)

Key rules:
- Core 'year' is the ONLY 'year' we keep.
- Core metadata (artist, title, chart, year_end_rank, echo_tier) is canonical.
- Audio CSV contributes only audio/ID feature columns (no metadata overrides).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple

from ma_config.paths import get_spine_root


def read_indexed_csv(path: Path, key_field: str) -> Tuple[Dict[str, dict], List[str]]:
    if not path.exists():
        raise SystemExit(f"[build_spine_master_v1] Missing CSV: {path}")

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"[build_spine_master_v1] Empty CSV or missing header: {path}")

        if key_field not in reader.fieldnames:
            raise SystemExit(
                f"[build_spine_master_v1] Key field '{key_field}' not found in {path} "
                f"header: {reader.fieldnames}"
            )

        rows: Dict[str, dict] = {}
        for row in reader:
            key = (row.get(key_field) or "").strip()
            if not key:
                # Skip rows without a key
                continue
            # Last one wins if duplicates, but we expect 1:1
            rows[key] = row

        return rows, list(reader.fieldnames)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Tier 1 master spine CSV (core + audio)."
    )
    default_root = get_spine_root()
    parser.add_argument(
        "--core",
        default=str(default_root / "spine_core_tracks_v1.csv"),
        help="Path to spine_core_tracks_v1.csv (canonical Year-End Top 40 metadata).",
    )
    parser.add_argument(
        "--audio",
        default=str(default_root / "spine_audio_spotify_v1_enriched.csv"),
        help="Path to spine_audio_spotify_v1_enriched.csv (audio features + IDs).",
    )
    parser.add_argument(
        "--out",
        default=str(default_root / "spine_master_v1.csv"),
        help="Output CSV path for master spine.",
    )

    args = parser.parse_args()

    core_path = Path(args.core).expanduser()
    audio_path = Path(args.audio).expanduser()
    out_path = Path(args.out).expanduser()

    print(f"[build_spine_master_v1] Loading core spine from: {core_path}")
    core_by_id, core_fields = read_indexed_csv(core_path, "spine_track_id")

    print(f"[build_spine_master_v1] Loading audio spine from: {audio_path}")
    audio_by_id, audio_fields_all = read_indexed_csv(audio_path, "spine_track_id")

    # Protect core metadata from being overwritten by audio CSV.
    # Anything in this set is *only* allowed to come from the core CSV.
    PROTECTED_FIELDS = {
        "spine_track_id",
        "year",
        "chart",
        "year_end_rank",
        "echo_tier",
        "artist",
        "title",
    }

    # Audio fields are everything in the audio CSV that is NOT a protected field.
    audio_fields: List[str] = [
        f for f in audio_fields_all if f not in PROTECTED_FIELDS
    ]

    # Final header = core fields (in original order) + any new audio fields
    fieldnames: List[str] = list(core_fields)
    for f in audio_fields:
        if f not in fieldnames:
            fieldnames.append(f)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[build_spine_master_v1] Writing master spine to: {out_path}")
    audio_match_count = 0

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for spine_id, core_row in core_by_id.items():
            # Start with pure core metadata row
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
        f"[build_spine_master_v1] Done. "
        f"Wrote {total} rows. Audio matched for {audio_match_count} / {total} spine tracks."
    )

    # Sanity logging: show if we accidentally lost 'year'
    if "year" not in fieldnames:
        print("[build_spine_master_v1][WARNING] 'year' missing from final header!")
    else:
        print("[build_spine_master_v1] 'year' column preserved from core spine.")


if __name__ == "__main__":
    main()
