#!/usr/bin/env python3
"""
spine_backfill_audio_v1.py

Backfill audio features for the Historical Echo Core Spine v1 (Core 1600)
using one or more pre-aligned audio sources.

This script does NOT try to map arbitrary external datasets directly.
Instead, you or other ETL scripts produce standardized "spine_audio_*.csv"
with spine_track_id already resolved.

Defaults resolve via env (MA_SPINE_ROOT) and can be overridden via CLI.
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, Any, List, Set

from ma_config.paths import get_spine_root


def load_csv_by_id(path: Path, key: str) -> Dict[str, dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        out: Dict[str, dict] = {}
        for row in reader:
            sid = row.get(key)
            if not sid:
                continue
            out[sid] = dict(row)
    return out


def load_csv_rows(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill audio features for Core Spine v1 using standardized "
            "audio sources that already contain spine_track_id."
        )
    )
    default_root = get_spine_root()
    parser.add_argument(
        "--core",
        default=str(default_root / "spine_core_tracks_v1.csv"),
        help="Core spine CSV path.",
    )
    parser.add_argument(
        "--base-audio",
        default=str(default_root / "spine_audio_spotify_v1.csv"),
        help="Base audio spine CSV (initial Kaggle/Spotify matches).",
    )
    parser.add_argument(
        "--extra-audio",
        action="append",
        default=[],
        help=(
            "Extra audio CSV(s) with spine_track_id + feature columns. "
            "Can be passed multiple times."
        ),
    )
    parser.add_argument(
        "--out",
        default=str(default_root / "spine_audio_spotify_v1_enriched.csv"),
        help="Output enriched audio CSV.",
    )

    args = parser.parse_args()

    core_path = Path(args.core).expanduser()
    base_audio_path = Path(args.base_audio).expanduser()
    out_path = Path(args.out).expanduser()
    extra_paths = [Path(p) for p in args.extra_audio]

    print(f"[INFO] Loading core spine from {core_path} ...")
    core_rows = load_csv_rows(core_path)
    core_ids: Set[str] = {r.get("spine_track_id") for r in core_rows if r.get("spine_track_id")}
    print(f"[INFO] Core spine has {len(core_ids)} unique spine_track_id values")

    print(f"[INFO] Loading base audio from {base_audio_path} ...")
    base_audio = load_csv_by_id(base_audio_path, "spine_track_id")
    base_ids: Set[str] = set(base_audio.keys())
    print(f"[INFO] Base audio covers {len(base_ids)} spine_track_id values")

    # Collect union of feature columns from base + extras
    base_fields: List[str]
    with base_audio_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        base_fields = reader.fieldnames or []

    id_like_cols = {"spine_track_id", "kaggle_track_id", "spotify_id"}
    feature_cols: Set[str] = set(c for c in base_fields if c not in id_like_cols)

    extra_audio_sources: List[Dict[str, dict]] = []
    for p in extra_paths:
        if not p.exists():
            print(f"[WARN] Extra audio source not found, skipping: {p}")
            continue

        print(f"[INFO] Loading extra audio source: {p} ...")
        src = load_csv_by_id(p, "spine_track_id")
        extra_audio_sources.append(src)

        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            for c in cols:
                if c not in id_like_cols:
                    feature_cols.add(c)

    # Put columns in a stable order: IDs first, then sorted features
    out_fieldnames = (
        ["spine_track_id", "kaggle_track_id", "spotify_id"]
        + sorted(feature_cols)
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Writing enriched audio spine to {out_path} ...")

    filled_from_extras = 0
    already_had_audio = 0
    total_core = len(core_ids)

    with out_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=out_fieldnames)
        writer.writeheader()

        for sid in sorted(core_ids):
            # Start with any existing base audio row
            row: Dict[str, Any] = {}
            base_row = base_audio.get(sid)
            if base_row is not None:
                already_had_audio += 1
                row.update(base_row)
            else:
                row["spine_track_id"] = sid
                row["kaggle_track_id"] = ""
                row["spotify_id"] = ""

            has_any_feature = any(
                (row.get(col) not in (None, "", "NaN"))
                for col in feature_cols
            )

            if not has_any_feature:
                for src in extra_audio_sources:
                    extra_row = src.get(sid)
                    if extra_row is None:
                        continue
                    for col in extra_row.keys():
                        if col not in out_fieldnames:
                            continue
                        val = extra_row.get(col)
                        if val not in (None, ""):
                            row[col] = val
                    has_any_feature = any(
                        (row.get(col) not in (None, "", "NaN"))
                        for col in feature_cols
                    )
                    if has_any_feature:
                        filled_from_extras += 1
                        break

            for col in out_fieldnames:
                row.setdefault(col, "")

            writer.writerow(row)

    print("[INFO] Backfill summary:")
    print(f"  Core tracks total          : {total_core}")
    print(f"  Already had audio (base)   : {already_had_audio}")
    print(f"  Newly filled from extras   : {filled_from_extras}")
    print(f"  Still missing audio        : {total_core - already_had_audio - filled_from_extras}")
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
