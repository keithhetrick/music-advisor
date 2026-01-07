#!/usr/bin/env python3
"""
historical_echo_backfill_tier3_audio.py

Backfill audio fields for Tier 3 lanes table using local *.features.json files.

- Table: spine_master_tier3_modern_lanes_v1 (default)
- Tiers stay additive; Tier 1 / Tier 2 are not modified.

Behavior:
- Walk a features root for *.features.json (default: features_output).
- Match features files to Tier 3 rows by normalized artist/title (slug logic).
- If tempo/loudness/valence are found, set has_audio=1, update audio fields,
  compute lane bands, and store audio_features_path (relative).
- If no match or missing audio fields, leave the row untouched.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools.spine.spine_slug import normalize_spine_text

TIER3_TABLE = "spine_master_tier3_modern_lanes_v1"
TIER3_LABEL = "EchoTier_3_YearEnd_Top200_Modern"


def safe_float(val: Any) -> Optional[float]:
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
    if tempo < 80:
        return "tempo_sub_80"
    if tempo < 100:
        return "tempo_80_100"
    if tempo < 120:
        return "tempo_100_120"
    if tempo < 140:
        return "tempo_120_140"
    return "tempo_over_140"


def band_valence(valence: Optional[float]) -> str:
    if valence is None:
        return ""
    if valence < 0.2:
        return "valence_very_low"
    if valence < 0.4:
        return "valence_low"
    if valence < 0.6:
        return "valence_mid"
    if valence < 0.8:
        return "valence_high"
    return "valence_very_high"


def band_energy(energy: Optional[float]) -> str:
    if energy is None:
        return ""
    if energy < 0.2:
        return "energy_very_low"
    if energy < 0.4:
        return "energy_low"
    if energy < 0.6:
        return "energy_mid"
    if energy < 0.8:
        return "energy_high"
    return "energy_very_high"


def band_loudness(loudness: Optional[float]) -> str:
    if loudness is None:
        return ""
    if loudness < -18:
        return "loudness_very_quiet"
    if loudness < -14:
        return "loudness_quiet"
    if loudness < -10:
        return "loudness_mid"
    if loudness < -6:
        return "loudness_loud"
    return "loudness_very_loud"


def pick_field(data: Dict[str, Any], candidates: Sequence[str]) -> Optional[float]:
    for key in candidates:
        if key in data and data[key] is not None:
            try:
                return float(data[key])
            except (TypeError, ValueError):
                continue
    return None


def load_feature_metrics(path: Path) -> Dict[str, Optional[float]]:
    data = json.loads(path.read_text())
    tempo = pick_field(
        data,
        [
            "tempo",
            "tempo_bpm",
            "estimated_tempo",
            "tempo_estimate_bpm",
            "tempo_global",
            "tempo_mean",
        ],
    )
    energy = pick_field(data, ["energy", "rms_energy", "energy_mean", "energy_global"])
    valence = pick_field(data, ["valence", "valence_mean", "valence_global"])
    loudness = pick_field(data, ["loudness_LUFS", "loudness", "integrated_LUFS", "loudness_integrated"])
    duration_ms = pick_field(data, ["duration_ms", "duration", "duration_millis"])
    return {
        "tempo": tempo,
        "energy": energy,
        "valence": valence,
        "loudness": loudness,
        "duration_ms": duration_ms,
    }


@dataclass
class FeatureFile:
    path: Path
    norm_path: str  # normalized stem/relpath for fuzzy matching


def build_feature_index(features_root: Path) -> List[FeatureFile]:
    features_root = features_root.resolve()
    index: List[FeatureFile] = []
    for feat_path in sorted(features_root.rglob("*.features.json")):
        rel = feat_path.relative_to(features_root)
        stem_norm = normalize_spine_text(rel.with_suffix("").as_posix())
        index.append(FeatureFile(path=feat_path, norm_path=stem_norm))
    return index


def find_match_for_slug(index: List[FeatureFile], artist: str, title: str) -> Optional[FeatureFile]:
    artist_norm = normalize_spine_text(artist)
    title_norm = normalize_spine_text(title)
    if not artist_norm or not title_norm:
        return None

    candidates: List[FeatureFile] = []
    for entry in index:
        if artist_norm in entry.norm_path and title_norm in entry.norm_path:
            candidates.append(entry)

    if not candidates:
        return None

    # Prefer the shortest normalized path (tends to be more specific)
    candidates.sort(key=lambda f: len(f.norm_path))
    return candidates[0]


def connect_db(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_absolute():
        db_path = REPO_ROOT / db_path
    if not db_path.is_file():
        raise FileNotFoundError(f"SQLite DB not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def backfill_tier3_audio(
    db_path: Path,
    table: str,
    features_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    conn = connect_db(db_path)
    try:
        cur = conn.execute(
            f"""
            SELECT id, spine_track_id, artist, title, slug,
                   tempo, energy, valence, loudness, duration_ms,
                   has_audio, audio_features_path
            FROM {table}
            WHERE echo_tier = ?
            """,
            (TIER3_LABEL,),
        )
        rows = cur.fetchall()

        print(f"[INFO] Loaded {len(rows)} rows from {table}")
        feature_index = build_feature_index(features_root)
        print(f"[INFO] Indexed {len(feature_index)} feature file(s) under {features_root}")

        updated = 0
        matched = 0
        for row in rows:
            has_audio = str(row["has_audio"] or "").strip()
            if has_audio in ("1", "true", "True") and not force:
                continue

            match = find_match_for_slug(feature_index, row["artist"], row["title"])
            if not match:
                continue

            metrics = load_feature_metrics(match.path)
            tempo = metrics["tempo"]
            valence = metrics["valence"]
            loudness = metrics["loudness"]
            energy = metrics["energy"]
            duration_ms = metrics["duration_ms"]

            if tempo is None or valence is None or loudness is None:
                continue

            matched += 1
            lane_fields = {
                "tempo_band": band_tempo(tempo),
                "valence_band": band_valence(valence),
                "energy_band": band_energy(energy),
                "loudness_band": band_loudness(loudness),
            }
            has_audio_val = "1"

            rel_path = match.path
            try:
                rel_path = match.path.relative_to(REPO_ROOT)
            except ValueError:
                rel_path = match.path
            rel_str = rel_path.as_posix()

            if dry_run:
                print(
                    f"[DRY-RUN] would update {row['spine_track_id']} "
                    f"({row['artist']} — {row['title']}) with {rel_str}"
                )
                continue

            conn.execute(
                f"""
                UPDATE {table}
                SET tempo = ?, valence = ?, loudness = ?, energy = ?, duration_ms = ?,
                    has_audio = ?, tempo_band = ?, valence_band = ?, energy_band = ?, loudness_band = ?,
                    audio_features_path = ?
                WHERE id = ?
                """,
                (
                    str(tempo),
                    str(valence),
                    str(loudness),
                    str(energy) if energy is not None else "",
                    str(int(duration_ms)) if duration_ms is not None else "",
                    has_audio_val,
                    lane_fields["tempo_band"],
                    lane_fields["valence_band"],
                    lane_fields["energy_band"],
                    lane_fields["loudness_band"],
                    rel_str,
                    row["id"],
                ),
            )
            updated += 1

        if not dry_run:
            conn.commit()
        print(f"[INFO] Matched feature files for {matched} rows; updated {updated} rows.")
    finally:
        conn.close()


def print_coverage(db_path: Path, table: str) -> None:
    db_path = db_path if db_path.is_absolute() else REPO_ROOT / db_path
    q_total = f"SELECT COUNT(*) AS total, SUM(has_audio <> 0) AS with_audio FROM {table};"
    q_years = (
        f"SELECT year, COUNT(*) AS tier3_tracks, SUM(has_audio <> 0) AS with_audio "
        f"FROM {table} GROUP BY year ORDER BY year;"
    )
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(q_total)
        total_row = cur.fetchone()
        print(f"[COVERAGE] total={total_row[0]} with_audio={total_row[1]}")
        print("[COVERAGE] Per-year:")
        for year, count, with_audio in conn.execute(q_years):
            print(f"  {year}: total={count}, with_audio={with_audio}")
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill Tier 3 audio/lanes using local features.")
    p.add_argument(
        "--db",
        default="data/historical_echo/historical_echo.db",
        help="SQLite DB path.",
    )
    p.add_argument(
        "--table",
        default=TIER3_TABLE,
        help="Tier 3 table name.",
    )
    p.add_argument(
        "--features-root",
        default="features_output",
        help="Root directory containing *.features.json files.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Update rows even if has_audio is already set.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show matches without updating DB.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    features_root = Path(args.features_root)

    if not features_root.exists():
        raise SystemExit(f"[ERROR] features-root does not exist: {features_root}")

    backfill_tier3_audio(
        db_path=db_path,
        table=args.table,
        features_root=features_root,
        force=args.force,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        print("[INFO] Coverage after backfill:")
        print_coverage(db_path, args.table)


if __name__ == "__main__":
    main()
