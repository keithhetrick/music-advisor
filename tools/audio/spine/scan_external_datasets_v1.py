#!/usr/bin/env python3
"""
Scan all CSVs under data/private/local_assets/external and surface strong audio-feature candidates.

Outputs a concise markdown report to data/private/local_assets/docs/DATASET_AUDIO_CANDIDATES.md with:
- relative path
- year coverage (min/max)
- artist/title column picks
- detected audio-feature columns
- quick notes (classification + header preview)
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


from shared.config.paths import get_external_data_root, get_local_assets_root


ROOT = get_external_data_root()
REPORT_PATH = get_local_assets_root() / "docs" / "DATASET_AUDIO_CANDIDATES.md"
DEFAULT_SAMPLE_LIMIT = 4000  # rows to sample per file for heuristics
DEFAULT_MAX_FILES = None     # optional cap on number of CSVs to scan

AUDIO_COLUMNS = {
    "tempo",
    "loudness",
    "danceability",
    "energy",
    "valence",
    "acousticness",
    "instrumentalness",
    "liveness",
    "speechiness",
    "duration_ms",
    "key",
    "mode",
    "time_signature",
    "tempo_bpm",
}

LYRIC_KEYS = {"lyrics", "line", "token", "word_count"}
YEAR_END_KEYS = {"year_end_rank", "year_end", "year-end", "year_end_position"}
WEEKLY_KEYS = {"weeks-on-board", "weeks_on_board", "last-week", "peak-rank", "date"}


@dataclass
class DatasetInfo:
    path: Path
    readable: bool
    kind: str = "other"
    fieldnames: List[str] = field(default_factory=list)
    audio_cols: List[str] = field(default_factory=list)
    artist_col: Optional[str] = None
    title_col: Optional[str] = None
    year_col: Optional[str] = None
    year_range: Optional[Tuple[int, int]] = None
    notes: List[str] = field(default_factory=list)

    @property
    def is_audio_candidate(self) -> bool:
        return bool(self.audio_cols and self.artist_col and self.title_col and self.year_col)


def classify(fieldnames: Iterable[str]) -> str:
    lower = {f.lower() for f in fieldnames}
    if AUDIO_COLUMNS & lower:
        return "audio_features"
    if LYRIC_KEYS & lower:
        return "lyrics"
    if YEAR_END_KEYS & lower:
        return "year_end_meta"
    if WEEKLY_KEYS & lower:
        return "weekly_chart"
    return "other"


def extract_year(raw: str) -> Optional[int]:
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    # direct integer
    if raw.isdigit() and len(raw) == 4:
        year = int(raw)
        if 1900 <= year <= 2100:
            return year
    # try to find a 4-digit year embedded in a date string
    m = re.search(r"(19|20)\d{2}", raw)
    if m:
        year = int(m.group(0))
        if 1900 <= year <= 2100:
            return year
    return None


def pick_best_col(candidates: List[str], counts: Dict[str, int], preferred_order: List[str]) -> Optional[str]:
    for keyword in preferred_order:
        for col in candidates:
            if keyword in col.lower() and counts.get(col, 0) > 0:
                return col
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def analyze_csv(path: Path, sample_limit: int) -> DatasetInfo:
    last_error: Optional[Exception] = None
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            with path.open("r", newline="", encoding=encoding) as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                fieldnames = list(reader.fieldnames)

                info = DatasetInfo(path=path, readable=True, fieldnames=fieldnames)
                info.kind = classify(fieldnames)

                lower_map = {name.lower(): name for name in fieldnames}
                audio_cols = [lower_map[name] for name in lower_map if name in AUDIO_COLUMNS]
                info.audio_cols = audio_cols

                artist_candidates = [name for name in fieldnames if any(k in name.lower() for k in ("artist", "performer", "singer", "band"))]
                title_candidates = [name for name in fieldnames if any(k in name.lower() for k in ("title", "track", "song", "name"))]
                year_candidates = [name for name in fieldnames if "year" in name.lower() or "date" in name.lower()]

                artist_counts: Dict[str, int] = {}
                title_counts: Dict[str, int] = {}
                year_counts: Dict[str, int] = {}
                year_values: List[int] = []

                rows_seen = 0
                for i, row in enumerate(reader):
                    rows_seen += 1
                    if i >= sample_limit:
                        break
                    for col in artist_candidates:
                        val = row.get(col, "")
                        if val and str(val).strip():
                            artist_counts[col] = artist_counts.get(col, 0) + 1
                    for col in title_candidates:
                        val = row.get(col, "")
                        if val and str(val).strip():
                            title_counts[col] = title_counts.get(col, 0) + 1
                    for col in year_candidates:
                        val = row.get(col, "")
                        year = extract_year(val)
                        if year:
                            year_counts[col] = year_counts.get(col, 0) + 1
                            year_values.append(year)

                info.artist_col = pick_best_col(artist_candidates, artist_counts, ["artist", "artists", "performer", "singer", "band"])
                info.title_col = pick_best_col(title_candidates, title_counts, ["title", "track", "song", "name"])
                info.year_col = pick_best_col(year_candidates, year_counts, ["year", "date", "release"])

                if year_values:
                    info.year_range = (min(year_values), max(year_values))

                cols_preview = ", ".join(fieldnames[:12])
                if len(fieldnames) > 12:
                    cols_preview += ", ..."
                info.notes.append(f"cols: {cols_preview}")
                if info.kind != "other":
                    info.notes.append(f"type: {info.kind}")
                if encoding != "utf-8":
                    info.notes.append(f"encoding: {encoding}")
                if not info.year_range:
                    info.notes.append("year range unknown")
                if rows_seen >= sample_limit:
                    info.notes.append(f"sampled first {rows_seen} rows (limit {sample_limit})")
                    if info.year_range:
                        info.notes.append("year range based on head sample")

                return info
        except Exception as exc:
            last_error = exc
            continue

    return DatasetInfo(path=path, readable=False, notes=[f"unreadable: {last_error}"])


def write_markdown(audio_candidates: List[DatasetInfo]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# DATASET AUDIO CANDIDATES\n\n")
        f.write("| Path | Year range | Artist col | Title col | Audio feature cols | Notes |\n")
        f.write("| ---- | ---------- | ---------- | --------- | ------------------ | ----- |\n")
        for info in audio_candidates:
            year_range = f"{info.year_range[0]}–{info.year_range[1]}" if info.year_range else "-"
            artist_col = info.artist_col or "-"
            title_col = info.title_col or "-"
            audio_cols = ", ".join(info.audio_cols) if info.audio_cols else "-"
            notes = "; ".join(info.notes)
            rel = info.path.relative_to(Path("."))
            f.write(f"| {rel} | {year_range} | {artist_col} | {title_col} | {audio_cols} | {notes} |\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan data/external for audio-capable CSVs.")
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=DEFAULT_SAMPLE_LIMIT,
        help="Rows to sample per CSV (higher = more accurate year range, slower).",
    )
    parser.add_argument(
        "--path-filter",
        nargs="+",
        help="Optional substrings; only CSV paths containing one of these will be scanned.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help="Optional cap on number of CSV files to scan (after filters).",
    )
    args = parser.parse_args()

    if not ROOT.exists():
        print(f"[scan_external_datasets_v1] Root not found: {ROOT}")
        return

    dataset_infos: List[DatasetInfo] = []
    scanned = 0
    for dirpath, _, filenames in os.walk(ROOT):
        for name in filenames:
            if not name.lower().endswith(".csv"):
                continue
            path = Path(dirpath) / name
            rel_str = str(path.relative_to(Path(".")))
            if args.path_filter and not any(frag.lower() in rel_str.lower() for frag in args.path_filter):
                continue
            if args.max_files is not None and scanned >= args.max_files:
                break
            info = analyze_csv(path, sample_limit=args.sample_limit)
            dataset_infos.append(info)
            scanned += 1
        if args.max_files is not None and scanned >= args.max_files:
            break

    audio_candidates = [d for d in dataset_infos if d.is_audio_candidate]
    write_markdown(audio_candidates)

    print(f"[scan_external_datasets_v1] scanned {len(dataset_infos)} CSV files under {ROOT}")
    print(f"[scan_external_datasets_v1] found {len(audio_candidates)} audio-capable candidates")
    print(f"[scan_external_datasets_v1] wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
