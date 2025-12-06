#!/usr/bin/env python3
"""
Merge TTC ground-truth tables (Harmonix + McGill) into a single reference file.

Precedence: Harmonix rows override McGill when (title, artist) collide (case-insensitive).

Input formats: CSV or JSON list of dicts with keys:
  song_id?, title, artist, ttc_seconds, source
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


Row = Dict[str, object]


def _load_rows(path: Path) -> List[Row]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text())
            return [dict(row) for row in data if isinstance(row, dict)]
        except Exception:
            return []
    rows: List[Row] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(dict(row))
    except Exception:
        return []
    return rows


def _dedupe(rows: Iterable[Row]) -> List[Row]:
    """
    Deduplicate by (title, artist) case-insensitive. Keeps first occurrence.
    """
    seen: set[Tuple[str, str]] = set()
    out: List[Row] = []
    for row in rows:
        title = str(row.get("title") or "").strip()
        artist = str(row.get("artist") or "").strip()
        key = (title.lower(), artist.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def merge_sources(harmonix: List[Row], mcgill: List[Row]) -> List[Row]:
    # Prefer Harmonix rows; append McGill where missing.
    merged: List[Row] = []
    merged.extend(_dedupe(harmonix))
    existing_keys = {(str(r.get("title") or "").strip().lower(), str(r.get("artist") or "").strip().lower()) for r in merged}
    for row in mcgill:
        key = (str(row.get("title") or "").strip().lower(), str(row.get("artist") or "").strip().lower())
        if key in existing_keys:
            continue
        merged.append(row)
    return merged


def write_csv(out: Path, rows: List[Row]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["song_id", "title", "artist", "ttc_seconds", "source"]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "song_id": row.get("song_id"),
                    "title": row.get("title"),
                    "artist": row.get("artist"),
                    "ttc_seconds": row.get("ttc_seconds"),
                    "source": row.get("source"),
                }
            )


def write_json(out: Path, rows: List[Row]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build consolidated TTC corpus (Harmonix preferred over McGill).")
    ap.add_argument("--harmonix", required=True, help="Path to Harmonix TTC CSV/JSON.")
    ap.add_argument("--mcgill", required=True, help="Path to McGill TTC CSV/JSON.")
    ap.add_argument("--out", required=True, help="Output CSV/JSON path.")
    ap.add_argument("--json", action="store_true", help="Write JSON instead of CSV.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    harmonix_rows = _load_rows(Path(args.harmonix).expanduser())
    mcgill_rows = _load_rows(Path(args.mcgill).expanduser())
    merged = merge_sources(harmonix_rows, mcgill_rows)
    if args.json or args.out.lower().endswith(".json"):
        write_json(Path(args.out), merged)
    else:
        write_csv(Path(args.out), merged)
    print(f"[build_ttc_corpus] merged {len(merged)} rows -> {args.out}")


if __name__ == "__main__":
    main()
