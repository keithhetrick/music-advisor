#!/usr/bin/env python3
"""
build_spine_master_tier3_modern_lanes_v1.py

Build Tier 3 lanes CSV (and optionally import into SQLite) for:
  EchoTier_3_YearEnd_Top200_Modern

Inputs:
  - Combined Year-End Hot 100 Top 200 CSV (default: data/private/local_assets/yearend_hot100/yearend_hot100_top200_1985_2024.csv)
    or a directory of per-year CSVs via --csv-root.
    Expected columns: year, rank (1-200), title, artist, optional spotify_id + audio feature columns.

Outputs:
  - data/public/spine/spine_master_tier3_modern_lanes_v1.csv
  - Optional DB import into spine_master_tier3_modern_lanes_v1 (reset with --reset)

Tier 1 and Tier 2 files remain untouched.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ma_audio_engine.adapters.bootstrap import ensure_repo_root
from shared.config.paths import get_spine_root, get_yearend_hot100_top200_path
from tools.spine.build_historical_spine_v1 import slugify
from tools.spine.spine_slug import make_spine_slug

ensure_repo_root()
CHART_DEFAULT = "hot_100_year_end_top200"
TIER_LABEL = "EchoTier_3_YearEnd_Top200_Modern"
SOURCE_CHART = "yearend_hot100_top200"
BILLBOARD_SOURCE = "YearEnd_Hot100_Top200"

RANK_COL_CANDIDATES = [
    "yearend_rank",
    "year_end_rank",
    "rank",
    "position",
    "year_end_position",
    "No.",
    "no",
]
TITLE_COL_CANDIDATES = [
    "title",
    "Title",
    "song",
    "name",
    "Track",
    "Track_Name",
    "Track_Name_clean",
]
ARTIST_COL_CANDIDATES = [
    "artist",
    "artists",
    "Artist",
    "Artist(s)",
    "performer",
    "Performer",
]
SPOTIFY_COL_CANDIDATES = ["spotify_id", "spotify_track_id", "spotify", "id"]
KAGGLE_COL_CANDIDATES = ["kaggle_track_id", "kaggle_id"]

FEATURE_COLS = [
    "acousticness",
    "audio_source",
    "danceability",
    "duration_ms",
    "energy",
    "instrumentalness",
    "key",
    "liveness",
    "loudness",
    "mode",
    "speechiness",
    "tempo",
    "time_signature",
    "valence",
]


@dataclass
class YearEndRow:
    year: int
    rank: int
    title: str
    artist: str
    spotify_id: str
    kaggle_track_id: str
    features: Dict[str, str]


def detect_col(fieldnames: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    for cand in candidates:
        if cand in fieldnames:
            return cand
    return None


def safe_float(val: str | None) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def band_tempo(tempo: Optional[float]) -> str:
    if tempo is None:
        return ""
    t = tempo
    if t < 80:
        return "tempo_sub_80"
    if t < 100:
        return "tempo_80_100"
    if t < 120:
        return "tempo_100_120"
    if t < 140:
        return "tempo_120_140"
    return "tempo_over_140"


def band_valence(valence: Optional[float]) -> str:
    if valence is None:
        return ""
    v = valence
    if v < 0.2:
        return "valence_very_low"
    if v < 0.4:
        return "valence_low"
    if v < 0.6:
        return "valence_mid"
    if v < 0.8:
        return "valence_high"
    return "valence_very_high"


def band_energy(energy: Optional[float]) -> str:
    if energy is None:
        return ""
    e = energy
    if e < 0.2:
        return "energy_very_low"
    if e < 0.4:
        return "energy_low"
    if e < 0.6:
        return "energy_mid"
    if e < 0.8:
        return "energy_high"
    return "energy_very_high"


def band_loudness(loudness: Optional[float]) -> str:
    if loudness is None:
        return ""
    l = loudness
    if l < -18:
        return "loudness_very_quiet"
    if l < -14:
        return "loudness_quiet"
    if l < -10:
        return "loudness_mid"
    if l < -6:
        return "loudness_loud"
    return "loudness_very_loud"


def make_spine_track_id(year: int, rank: int, artist: str, title: str) -> str:
    """Tier 3 spine_track_id with chart slug distinguishing Top 200."""
    chart_slug = slugify(CHART_DEFAULT, max_len=24)
    artist_slug = slugify(artist, max_len=24)
    title_slug = slugify(title, max_len=24)
    return f"{year}_{chart_slug}_{rank:03d}_{artist_slug}_{title_slug}"


def load_year_end_rows(path: Path, year_min: int, year_max: int) -> List[YearEndRow]:
    rows: List[YearEndRow] = []
    if not path.is_file():
        raise SystemExit(f"[ERROR] Year-End CSV not found: {path}")

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        # Normalize fieldnames by stripping whitespace for robustness
        fields = [fn.strip() if isinstance(fn, str) else fn for fn in (reader.fieldnames or [])]
        reader.fieldnames = fields

        rank_col = detect_col(fields, RANK_COL_CANDIDATES)
        title_col = detect_col(fields, TITLE_COL_CANDIDATES)
        artist_col = detect_col(fields, ARTIST_COL_CANDIDATES)
        spotify_col = detect_col(fields, SPOTIFY_COL_CANDIDATES)
        kaggle_col = detect_col(fields, KAGGLE_COL_CANDIDATES)

        if rank_col is None or title_col is None or artist_col is None:
            raise SystemExit(
                f"[ERROR] Missing expected columns in {path}. "
                f"Found: {fields}. Need rank/title/artist."
            )

        for raw in reader:
            try:
                year_val = int((raw.get("year") or raw.get("Year") or raw.get("year ") or "").strip())
            except (ValueError, AttributeError):
                continue
            if year_val < year_min or year_val > year_max:
                continue

            rank_raw = (raw.get(rank_col) or "").strip()
            try:
                rank = int(rank_raw)
            except ValueError:
                continue
            if rank < 1 or rank > 200:
                continue

            title = (raw.get(title_col) or "").strip()
            artist = (raw.get(artist_col) or "").strip()
            spotify_id = (raw.get(spotify_col) or "").strip() if spotify_col else ""
            kaggle_track_id = (raw.get(kaggle_col) or "").strip() if kaggle_col else ""
            if not title or not artist:
                continue

            feat_values: Dict[str, str] = {}
            for feat in FEATURE_COLS:
                val = raw.get(feat)
                feat_values[feat] = (val or "").strip() if isinstance(val, str) else ("" if val is None else str(val))

            rows.append(
                YearEndRow(
                    year=year_val,
                    rank=rank,
                    title=title,
                    artist=artist,
                    spotify_id=spotify_id,
                    kaggle_track_id=kaggle_track_id,
                    features=feat_values,
                )
            )
    return rows


def gather_input_paths(input_csv: Optional[Path], csv_root: Optional[Path]) -> List[Path]:
    if input_csv and input_csv.exists():
        return [input_csv]
    if csv_root and csv_root.is_dir():
        return sorted([p for p in csv_root.glob("*.csv") if p.is_file()])
    raise SystemExit("[ERROR] Provide --input-csv or --csv-root with at least one CSV file.")


def compute_lane_fields(row: YearEndRow) -> Dict[str, str]:
    tempo = safe_float(row.features.get("tempo"))
    loudness = safe_float(row.features.get("loudness"))
    valence = safe_float(row.features.get("valence"))
    energy = safe_float(row.features.get("energy"))

    has_audio = int(tempo is not None and loudness is not None and valence is not None)

    lane_fields = {
        "has_audio": has_audio,
        "tempo_band": band_tempo(tempo) if has_audio else "",
        "valence_band": band_valence(valence) if has_audio else "",
        "energy_band": band_energy(energy) if has_audio else "",
        "loudness_band": band_loudness(loudness) if has_audio else "",
    }
    return {k: str(v) for k, v in lane_fields.items()}


def write_lanes(out_path: Path, rows: List[YearEndRow]) -> List[str]:
    fieldnames = [
        "spine_track_id",
        "slug",
        "year",
        "chart",
        "year_end_rank",
        "echo_tier",
        "tier_label",
        "source_chart",
        "artist",
        "title",
        "billboard_source",
        "spotify_id",
        "notes",
        "kaggle_track_id",
        "acousticness",
        "audio_source",
        "danceability",
        "duration_ms",
        "energy",
        "instrumentalness",
        "key",
        "liveness",
        "loudness",
        "mode",
        "speechiness",
        "tempo",
        "time_signature",
        "valence",
        "has_audio",
        "tempo_band",
        "valence_band",
        "energy_band",
        "loudness_band",
        "audio_features_path",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in sorted(rows, key=lambda x: (x.year, x.rank)):
            lane_fields = compute_lane_fields(r)
            row_dict: Dict[str, str] = {
                "spine_track_id": make_spine_track_id(r.year, r.rank, r.artist, r.title),
                "slug": make_spine_slug(r.title, r.artist),
                "year": str(r.year),
                "chart": CHART_DEFAULT,
                "year_end_rank": str(r.rank),
                "echo_tier": TIER_LABEL,
                "tier_label": TIER_LABEL,
                "source_chart": SOURCE_CHART,
                "artist": r.artist,
                "title": r.title,
                "billboard_source": BILLBOARD_SOURCE,
                "spotify_id": r.spotify_id,
                "notes": "",
                "kaggle_track_id": r.kaggle_track_id,
                "audio_features_path": "",
            }
            for feat in FEATURE_COLS:
                row_dict[feat] = r.features.get(feat, "")
            row_dict.update(lane_fields)
            writer.writerow(row_dict)

    return fieldnames


def import_into_db(csv_path: Path, db_path: Path, table: str, fieldnames: List[str], reset: bool) -> None:
    db_path = db_path if db_path.is_absolute() else (REPO_ROOT / db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        if reset:
            cur.execute(f'DROP TABLE IF EXISTS "{table}"')

        cols: List[str] = []
        seen = set()
        for name in fieldnames:
            name = (name or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            cols.append(name)

        col_defs = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
        for name in cols:
            col_defs.append(f'"{name}" TEXT')

        cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})')
        conn.commit()

        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(f'"{c}"' for c in cols)
        insert_sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

        inserted = 0
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                values = [row.get(c, "") for c in cols]
                cur.execute(insert_sql, values)
                inserted += 1
        conn.commit()
        print(f"[INFO] Inserted {inserted} rows into {table} @ {db_path}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Tier 3 lanes CSV (Top 200 Year-End Hot 100, 1985–2024).")
    parser.add_argument(
        "--input-csv",
        default=str(get_yearend_hot100_top200_path()),
        help="Combined Year-End Top 200 CSV.",
    )
    parser.add_argument(
        "--csv-root",
        default=None,
        help="Optional directory of per-year CSVs (uses all *.csv files within).",
    )
    parser.add_argument(
        "--out",
        default=str(get_spine_root() / "spine_master_tier3_modern_lanes_v1.csv"),
        help="Output Tier 3 lanes CSV path.",
    )
    parser.add_argument(
        "--year-min",
        type=int,
        default=1985,
        help="Minimum year to include.",
    )
    parser.add_argument(
        "--year-max",
        type=int,
        default=2024,
        help="Maximum year to include.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Optional SQLite DB path to import into (e.g., data/private/local_assets/historical_echo/historical_echo.db).",
    )
    parser.add_argument(
        "--table",
        default="spine_master_tier3_modern_lanes_v1",
        help="Destination table name when importing.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the destination table before import.",
    )

    args = parser.parse_args()

    input_csv = Path(args.input_csv) if args.input_csv else None
    csv_root = Path(args.csv_root) if args.csv_root else None
    out_path = Path(args.out)

    input_paths = gather_input_paths(input_csv, csv_root)
    print(f"[INFO] Loading {len(input_paths)} Year-End CSV file(s):")
    for p in input_paths:
        print(f"  - {p}")

    all_rows: List[YearEndRow] = []
    for p in input_paths:
        rows = load_year_end_rows(p, args.year_min, args.year_max)
        print(f"[INFO]   {p}: {len(rows)} row(s) within {args.year_min}-{args.year_max} and rank 1-200")
        all_rows.extend(rows)

    if not all_rows:
        print("[WARN] No rows loaded; nothing to write.")
        return

    print(f"[INFO] Writing Tier 3 lanes CSV to {out_path} ...")
    fieldnames = write_lanes(out_path, all_rows)
    print(f"[INFO] Wrote {len(all_rows)} rows -> {out_path}")

    # Per-year counts
    per_year: Dict[int, int] = {}
    for r in all_rows:
        per_year[r.year] = per_year.get(r.year, 0) + 1
    print("[INFO] Per-year counts (loaded):")
    for year in sorted(per_year):
        print(f"  {year}: {per_year[year]}")

    if args.db:
        db_path = Path(args.db)
        print(f"[INFO] Importing into DB: {db_path} (table={args.table}, reset={args.reset})")
        import_into_db(out_path, db_path, args.table, fieldnames, reset=args.reset)


if __name__ == "__main__":
    main()
