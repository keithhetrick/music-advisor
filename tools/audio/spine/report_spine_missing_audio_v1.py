#!/usr/bin/env python3
"""
Report Tier 1 spine tracks that still have has_audio = 0.

Inputs:
    - data/spine/spine_master_v1_lanes.csv  (lane-ified Tier 1)

Outputs:
    - data/spine/reports/spine_missing_audio_v1.csv
        Columns:
            spine_track_id
            year
            year_end_rank
            artist
            title
            chart
            echo_tier
            has_audio
    - Prints a small summary (total missing and per-year breakdown).
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Dict

from ma_config.paths import get_spine_root


def safe_int(val: str, default: int | None = None) -> int | None:
    if val is None:
        return default
    s = str(val).strip()
    if not s:
        return default
    try:
        return int(s)
    except ValueError:
        return default


def main() -> None:
    spine_root = get_spine_root()
    lanes_path = spine_root / "spine_master_v1_lanes.csv"
    out_path = spine_root / "reports" / "spine_missing_audio_v1.csv"

    if not lanes_path.exists():
        raise SystemExit(
            f"[report_spine_missing_audio_v1] Missing lanes CSV: {lanes_path}"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with lanes_path.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        if not reader.fieldnames:
            raise SystemExit(
                f"[report_spine_missing_audio_v1] Lanes CSV has no header: {lanes_path}"
            )

        fieldnames_in: List[str] = list(reader.fieldnames)

        required_fields = [
            "spine_track_id",
            "year",
            "year_end_rank",
            "artist",
            "title",
            "chart",
            "echo_tier",
            "has_audio",
        ]
        for rf in required_fields:
            if rf not in fieldnames_in:
                raise SystemExit(
                    f"[report_spine_missing_audio_v1] Required field '{rf}' "
                    f"not found in lanes CSV header: {fieldnames_in}"
                )

        missing_rows: List[Dict[str, str]] = []
        per_year_counts: Counter[int] = Counter()

        for row in reader:
            has_audio_val = (row.get("has_audio") or "").strip()
            has_audio_flag = safe_int(has_audio_val, default=0) or 0

            if has_audio_flag != 0:
                # Only interested in missing audio
                continue

            year = safe_int(row.get("year"), default=-1)
            if year is not None:
                per_year_counts[year] += 1

            out_row = {
                "spine_track_id": (row.get("spine_track_id") or "").strip(),
                "year": row.get("year", "").strip(),
                "year_end_rank": row.get("year_end_rank", "").strip(),
                "artist": row.get("artist", "").strip(),
                "title": row.get("title", "").strip(),
                "chart": row.get("chart", "").strip(),
                "echo_tier": row.get("echo_tier", "").strip(),
                "has_audio": has_audio_val,
            }
            missing_rows.append(out_row)

    # Write CSV
    out_fieldnames = [
        "spine_track_id",
        "year",
        "year_end_rank",
        "artist",
        "title",
        "chart",
        "echo_tier",
        "has_audio",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=out_fieldnames)
        writer.writeheader()
        for row in missing_rows:
            writer.writerow(row)

    total_missing = len(missing_rows)
    print(
        f"[report_spine_missing_audio_v1] Wrote {total_missing} rows "
        f"to {out_path}"
    )

    # Sorted per-year summary
    print("[report_spine_missing_audio_v1] Missing per year:")
    for year in sorted(per_year_counts.keys()):
        print(f"  {year}: {per_year_counts[year]} tracks without audio")


if __name__ == "__main__":
    main()
