#!/usr/bin/env python3
"""
Extract TTC (time-to-chorus) ground truth from the Harmonix Set.

Inputs:
- segments/ directory containing per-track .txt/.tsv files with timestamped labels.
- metadata.tsv mapping track IDs to title/artist (and optional MBID).

Outputs:
- CSV or JSON rows with: song_id (track id/MBID), title, artist, ttc_seconds, source="Harmonix".
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

SOURCE = "Harmonix"


def _parse_timestamp(token: str) -> Optional[float]:
    token = token.strip()
    if not token:
        return None
    try:
        if ":" in token:
            parts = token.split(":")
            val = 0.0
            for part in parts:
                val = val * 60 + float(part)
            return float(val)
        return float(token)
    except Exception:
        return None


def _load_metadata(meta_path: Path) -> Dict[str, Dict[str, str]]:
    meta: Dict[str, Dict[str, str]] = {}
    if not meta_path.exists():
        return meta
    with meta_path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            track_id = parts[0].strip()
            title = parts[1].strip()
            artist = parts[2].strip() if len(parts) > 2 else "Unknown"
            mbid = parts[3].strip() if len(parts) > 3 else ""
            meta[track_id] = {
                "title": title or track_id,
                "artist": artist or "Unknown",
                "song_id": mbid or track_id,
            }
    return meta


def _find_first_chorus(path: Path) -> Optional[float]:
    try:
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", "\t").split("\t")
            parts = [p for p in parts if p]
            if not parts:
                continue
            ts = _parse_timestamp(parts[0])
            label = parts[-1].lower() if parts else ""
            if "chorus" in label and ts is not None:
                return ts
    except Exception:
        return None
    return None


def extract_rows(segments_dir: Path, meta_path: Path) -> List[Dict[str, object]]:
    meta = _load_metadata(meta_path)
    rows: List[Dict[str, object]] = []
    for path in sorted(segments_dir.glob("**/*")):
        if path.is_dir() or path.suffix.lower() not in {".txt", ".tsv"}:
            continue
        ttc = _find_first_chorus(path)
        track_id = path.stem
        info = meta.get(track_id, {})
        rows.append(
            {
                "song_id": info.get("song_id", track_id),
                "title": info.get("title", track_id),
                "artist": info.get("artist", "Unknown"),
                "ttc_seconds": ttc,
                "source": SOURCE,
                "path": str(path),
            }
        )
    return rows


def write_csv(out: Path, rows: Iterable[Dict[str, object]]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    rows_list = list(rows)
    fieldnames = ["song_id", "title", "artist", "ttc_seconds", "source", "path"]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_list:
            writer.writerow(row)


def write_json(out: Path, rows: Iterable[Dict[str, object]]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    rows_list = list(rows)
    out.write_text(json.dumps(rows_list, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Extract TTC from Harmonix annotations.")
    ap.add_argument("--segments-dir", required=True, help="Directory containing Harmonix segment files.")
    ap.add_argument("--metadata", required=True, help="Path to metadata.tsv mapping track IDs to title/artist/MBID.")
    ap.add_argument("--out", required=True, help="Output CSV/JSON path.")
    ap.add_argument("--json", action="store_true", help="Write JSON instead of CSV.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    segments_dir = Path(args.segments_dir).expanduser()
    meta_path = Path(args.metadata).expanduser()
    if not segments_dir.exists():
        raise SystemExit(f"Segments directory does not exist: {segments_dir}")
    rows = extract_rows(segments_dir, meta_path)
    if args.json or args.out.lower().endswith(".json"):
        write_json(Path(args.out), rows)
    else:
        write_csv(Path(args.out), rows)
    print(f"[ttc_extract_from_harmonix] wrote {len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
