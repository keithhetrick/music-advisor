#!/usr/bin/env python3
"""
build_historical_spine_v1.py

# Historical Echo Core Spine v1 ("Core 1600"):
# 1985–2024, Year-End Top 40 per year from hci_v2_targets_pop_us_1985_2024.csv
# -> strongest historical echo tier: EchoTier_1_YearEnd_Top40

Builds Music Advisor Historical Spine & Echo Tiers v1 from:

- Billboard Year-End style CSV (UT Austin-derived).
- Kaggle/Spotify-style tracks CSV.

Outputs (defaults resolve via MA_SPINE_ROOT / MA_DATA_ROOT):
- spine_core_tracks_<version>.csv
- spine_audio_spotify_<version>.csv
- spine_unmatched_billboard_<version>.csv
- historical_spine_build_<version>_summary.txt

This script is intentionally "boring and reproducible":
- Pure Python stdlib (csv, re, statistics).
- Deterministic matching rules.
"""

import argparse
import csv
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ma_config.paths import get_spine_root, get_data_root
from shared.config.paths import get_external_data_root, get_hci_v2_targets_csv

# ------------- Echo Tier Logic -------------

def compute_echo_tier(rank: int) -> Optional[str]:
    if 1 <= rank <= 40:
        return "EchoTier_1_YearEnd_Top40"
    if 41 <= rank <= 100:
        return "EchoTier_2_YearEnd_41_100"
    if 101 <= rank <= 200:
        return "EchoTier_3_YearEnd_101_200"
    return None


# ------------- Normalization Helpers -------------

PUNCT_RE = re.compile(r"[^\w\s]")
PARENS_RE = re.compile(r"[\(\[].*?[\)\]]")

def normalize_text(s: str) -> str:
    """
    Lower, strip, remove bracketed parts, kill 'feat.' segments, remove punctuation, normalize whitespace.
    Deterministic and intentionally simple.
    """
    s = s or ""
    s = s.lower()
    # Remove bracketed chunks like "(feat. X)" or "[Remix]"
    s = PARENS_RE.sub(" ", s)
    # Remove common featuring markers
    for token in [" feat. ", " featuring ", " ft. ", " feat ", " ft "]:
        s = s.replace(token, " ")
    # Remove punctuation
    s = PUNCT_RE.sub(" ", s)
    # Collapse whitespace
    s = " ".join(s.split())
    return s


SLUG_RE = re.compile(r"[^a-z0-9]+")

def slugify(s: str, max_len: int = 32) -> str:
    s = s.lower()
    s = SLUG_RE.sub("-", s)
    s = s.strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "na"


def make_spine_track_id(year: int, chart: str, rank: int, artist: str, title: str) -> str:
    """
    Stable, human-readable ID based on (year, chart, rank, artist, title).
    """
    chart_slug = slugify(chart, max_len=16)
    artist_slug = slugify(artist, max_len=24)
    title_slug = slugify(title, max_len=24)
    return f"{year}_{chart_slug}_{rank:03d}_{artist_slug}_{title_slug}"


# ------------- Billboard (UT) Loader -------------

YEAR_END_RANK_CANDIDATES = ["year_end_rank", "year_end_position", "rank"]

@dataclass
class BillboardRow:
    year: int
    chart: str
    rank: int
    artist: str
    title: str
    spotify_id: str
    raw_row: Dict[str, str]


def detect_rank_column(fieldnames: List[str]) -> str:
    for cand in YEAR_END_RANK_CANDIDATES:
        if cand in fieldnames:
            return cand
    raise RuntimeError(
        f"Could not find a year-end rank column in {fieldnames}. "
        f"Tried: {YEAR_END_RANK_CANDIDATES}"
    )


def load_billboard_rows(path: Path, chart_default: str, year_min: int, year_max: int) -> List[BillboardRow]:
    rows: List[BillboardRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rank_col = detect_rank_column(reader.fieldnames or [])

        for raw in reader:
            try:
                year = int((raw.get("year") or "").strip())
            except ValueError:
                continue
            if year < year_min or year > year_max:
                continue

            chart = (raw.get("chart") or chart_default).strip()

            rank_raw = (raw.get(rank_col) or "").strip()
            if not rank_raw:
                continue
            try:
                rank = int(rank_raw)
            except ValueError:
                continue

            echo_tier = compute_echo_tier(rank)
            if echo_tier is None:
                continue  # > 200 out of scope

            artist = (raw.get("artist") or raw.get("Artist") or "").strip()
            title = (raw.get("title") or raw.get("song") or raw.get("Song") or "").strip()
            spotify_id = (raw.get("spotify_id") or raw.get("spotify_track_id") or "").strip()

            if not artist or not title:
                continue

            rows.append(
                BillboardRow(
                    year=year,
                    chart=chart,
                    rank=rank,
                    artist=artist,
                    title=title,
                    spotify_id=spotify_id,
                    raw_row=raw,
                )
            )

    return rows


# ------------- Kaggle Tracks Loader -------------

@dataclass
class KaggleTrack:
    idx: int
    kaggle_track_id: str
    spotify_id: str
    artist: str
    title: str
    year: Optional[int]
    raw_row: Dict[str, str]


def detect_col(fieldnames: List[str], candidates: List[str]) -> Optional[str]:
    for cand in candidates:
        if cand in fieldnames:
            return cand
    return None


def load_kaggle_tracks(path: Path) -> Tuple[List[KaggleTrack], Dict[str, KaggleTrack], Dict[str, List[KaggleTrack]]]:
    tracks: List[KaggleTrack] = []
    by_spotify_id: Dict[str, KaggleTrack] = {}
    by_norm_name: Dict[str, List[KaggleTrack]] = defaultdict(list)

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        id_col = detect_col(fields, ["id", "spotify_id", "track_id"])
        if not id_col:
            raise RuntimeError(f"Could not find Kaggle track id column in {fields}")

        title_col = detect_col(fields, ["track_name", "name", "title"])
        artist_col = detect_col(fields, ["artist", "artists"])
        year_col = detect_col(fields, ["year", "release_year"])

        for idx, raw in enumerate(reader):
            kaggle_track_id = (raw.get(id_col) or "").strip()
            if not kaggle_track_id:
                continue

            title = (raw.get(title_col) or "").strip() if title_col else ""
            artist = (raw.get(artist_col) or "").strip() if artist_col else ""
            spotify_id = (raw.get("spotify_id") or raw.get("id") or "").strip()

            year_val: Optional[int] = None
            if year_col:
                y_raw = (raw.get(year_col) or "").strip()
                if y_raw:
                    try:
                        year_val = int(y_raw)
                    except ValueError:
                        year_val = None

            kt = KaggleTrack(
                idx=idx,
                kaggle_track_id=kaggle_track_id,
                spotify_id=spotify_id,
                artist=artist,
                title=title,
                year=year_val,
                raw_row=raw,
            )
            tracks.append(kt)

            if spotify_id:
                by_spotify_id.setdefault(spotify_id, kt)

            norm_key = f"{normalize_text(artist)}||{normalize_text(title)}"
            if norm_key.strip(" |"):
                by_norm_name[norm_key].append(kt)

    return tracks, by_spotify_id, by_norm_name


# ------------- Matching Logic -------------

@dataclass
class MatchResult:
    spine_track_id: str
    bb: BillboardRow
    kaggle_track: Optional[KaggleTrack]
    match_type: str  # "spotify_id", "name_exact", "name_year_tiebreak", ""


def match_billboard_to_kaggle(
    billboard_rows: List[BillboardRow],
    kaggle_by_spotify_id: Dict[str, KaggleTrack],
    kaggle_by_norm_name: Dict[str, List[KaggleTrack]],
) -> List[MatchResult]:
    results: List[MatchResult] = []

    for bb in billboard_rows:
        chart = bb.chart or "hot_100_year_end"
        spine_id = make_spine_track_id(bb.year, chart, bb.rank, bb.artist, bb.title)

        match_type = ""
        matched_kt: Optional[KaggleTrack] = None

        # 1) Direct spotify_id match
        if bb.spotify_id:
            kt = kaggle_by_spotify_id.get(bb.spotify_id)
            if kt:
                match_type = "spotify_id"
                matched_kt = kt

        # 2) Normalized name match
        if matched_kt is None:
            norm_key = f"{normalize_text(bb.artist)}||{normalize_text(bb.title)}"
            candidates = kaggle_by_norm_name.get(norm_key, [])

            if len(candidates) == 1:
                matched_kt = candidates[0]
                match_type = "name_exact"
            elif len(candidates) > 1:
                # Deterministic tie-breaker: closest year
                best = None
                best_score = None
                for kt in candidates:
                    if kt.year is None:
                        score = 9999
                    else:
                        score = abs(kt.year - bb.year)
                    if best is None or score < best_score:
                        best = kt
                        best_score = score
                matched_kt = best
                match_type = "name_year_tiebreak"

        results.append(
            MatchResult(
                spine_track_id=spine_id,
                bb=bb,
                kaggle_track=matched_kt,
                match_type=match_type,
            )
        )

    return results


# ------------- Output Writers -------------

def write_spine_core_tracks(
    out_path: Path,
    matches: List[MatchResult],
) -> None:
    fieldnames = [
        "spine_track_id",
        "year",
        "chart",
        "year_end_rank",
        "echo_tier",
        "artist",
        "title",
        "billboard_source",
        "spotify_id",
        "kaggle_track_id",
        "kaggle_match_type",
        "notes",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for m in matches:
            bb = m.bb
            echo_tier = compute_echo_tier(bb.rank)
            if echo_tier is None:
                continue

            kaggle_id = m.kaggle_track.kaggle_track_id if m.kaggle_track else ""
            row = {
                "spine_track_id": m.spine_track_id,
                "year": bb.year,
                "chart": bb.chart,
                "year_end_rank": bb.rank,
                "echo_tier": echo_tier,
                "artist": bb.artist,
                "title": bb.title,
                "billboard_source": "UT_Austin_rwd_billboard_year_end",
                "spotify_id": bb.spotify_id,
                "kaggle_track_id": kaggle_id,
                "kaggle_match_type": m.match_type,
                "notes": "",
            }
            writer.writerow(row)


def write_spine_audio_spotify(
    out_path: Path,
    matches: List[MatchResult],
    numeric_feature_cols: List[str],
) -> None:
    """
    Only writes rows for matched Kaggle tracks.
    numeric_feature_cols should be columns that exist in Kaggle raw_row.
    """
    base_cols = [
        "spine_track_id",
        "kaggle_track_id",
        "spotify_id",
    ]
    fieldnames = base_cols + numeric_feature_cols

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for m in matches:
            if m.kaggle_track is None:
                continue
            kt = m.kaggle_track
            row = {
                "spine_track_id": m.spine_track_id,
                "kaggle_track_id": kt.kaggle_track_id,
                "spotify_id": kt.spotify_id,
            }
            for col in numeric_feature_cols:
                v_raw = kt.raw_row.get(col)
                if v_raw is None or v_raw == "":
                    row[col] = ""
                    continue
                try:
                    if col.endswith("_ms") or col in ("duration_ms", "time_signature", "key", "mode"):
                        row[col] = int(float(v_raw))
                    else:
                        row[col] = float(v_raw)
                except ValueError:
                    row[col] = ""
            writer.writerow(row)


def write_unmatched_billboard(
    out_path: Path,
    matches: List[MatchResult],
) -> None:
    fieldnames = [
        "year",
        "chart",
        "year_end_rank",
        "echo_tier",
        "artist",
        "title",
        "spotify_id",
        "normalized_artist",
        "normalized_title",
        "matching_attempts",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for m in matches:
            if m.kaggle_track is not None:
                continue
            bb = m.bb
            echo_tier = compute_echo_tier(bb.rank)
            if echo_tier is None:
                continue

            norm_artist = normalize_text(bb.artist)
            norm_title = normalize_text(bb.title)
            attempts = []
            if bb.spotify_id:
                attempts.append("spotify_id")
            attempts.append("normalized_name")
            row = {
                "year": bb.year,
                "chart": bb.chart,
                "year_end_rank": bb.rank,
                "echo_tier": echo_tier,
                "artist": bb.artist,
                "title": bb.title,
                "spotify_id": bb.spotify_id,
                "normalized_artist": norm_artist,
                "normalized_title": norm_title,
                "matching_attempts": ",".join(attempts),
            }
            writer.writerow(row)


# ------------- Summary Stats -------------

def summarize(matches: List[MatchResult], numeric_feature_cols: List[str]) -> str:
    """
    Returns a human-readable summary string: counts per tier, match rates, and simple
    feature stats (mean/min/max) per tier.
    """
    tier_counts = defaultdict(int)
    tier_match_counts = defaultdict(int)
    feature_values = defaultdict(lambda: defaultdict(list))  # tier -> col -> [vals]

    for m in matches:
        echo_tier = compute_echo_tier(m.bb.rank)
        if echo_tier is None:
            continue
        tier_counts[echo_tier] += 1
        if m.kaggle_track is not None:
            tier_match_counts[echo_tier] += 1
            for col in numeric_feature_cols:
                v_raw = m.kaggle_track.raw_row.get(col)
                if v_raw is None or v_raw == "":
                    continue
                try:
                    val = float(v_raw)
                except ValueError:
                    continue
                feature_values[echo_tier][col].append(val)

    lines: List[str] = []
    lines.append("=== Historical Spine v1 Summary ===")
    total = sum(tier_counts.values())
    total_matched = sum(tier_match_counts.values())
    if total:
        lines.append(f"Total Billboard Year-End tracks (<=200): {total}")
        lines.append(f"Total with Kaggle match: {total_matched} ({(total_matched/total*100):.1f}%)")
    else:
        lines.append("No tracks found in given year range.")

    lines.append("")
    lines.append("Per Echo Tier:")
    for tier in sorted(tier_counts.keys()):
        cnt = tier_counts[tier]
        mcnt = tier_match_counts[tier]
        pct = (mcnt / cnt * 100) if cnt else 0.0
        lines.append(f"- {tier}: {cnt} tracks, {mcnt} matched ({pct:.1f}%)")

    lines.append("")
    lines.append("Basic feature stats (mean / min / max) by tier:")
    for tier in sorted(feature_values.keys()):
        lines.append(f"Tier: {tier}")
        for col in numeric_feature_cols:
            vals = feature_values[tier].get(col, [])
            if not vals:
                continue
            mean_v = statistics.mean(vals)
            min_v = min(vals)
            max_v = max(vals)
            lines.append(f"  {col}: mean={mean_v:.3f}, min={min_v:.3f}, max={max_v:.3f}")
        lines.append("")

    return "\n".join(lines)


# ------------- CLI -------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build Music Advisor Historical Spine & Echo Tiers v1")
    parser.add_argument(
        "--billboard-csv",
        default=str(get_hci_v2_targets_csv()),
        help="Input Billboard Year-End style CSV (UT Austin-derived)",
    )
    parser.add_argument(
        "--tracks-csv",
        default=str(get_external_data_root() / "tracks.csv"),
        help="Input Kaggle/Spotify-style tracks.csv",
    )
    parser.add_argument(
        "--out-dir",
        default=str(get_spine_root()),
        help="Output directory for spine CSVs",
    )
    parser.add_argument(
        "--version",
        default="v1",
        help="Spine version tag, used in output filenames (e.g. v1, v1_1)",
    )
    parser.add_argument(
        "--year-min",
        type=int,
        default=1985,
        help="Minimum chart year to include",
    )
    parser.add_argument(
        "--year-max",
        type=int,
        default=2024,
        help="Maximum chart year to include",
    )
    parser.add_argument(
        "--chart-default",
        default="hot_100_year_end",
        help="Default chart name if not present in Billboard CSV",
    )

    args = parser.parse_args()

    bb_path = Path(args.billboard_csv).expanduser()
    kg_path = Path(args.tracks_csv).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Loading Billboard Year-End rows from {bb_path} ...")
    bb_rows = load_billboard_rows(bb_path, args.chart_default, args.year_min, args.year_max)
    print(f"[INFO] Loaded {len(bb_rows)} Billboard rows within {args.year_min}-{args.year_max} and rank <= 200")

    print(f"[INFO] Loading Kaggle tracks from {kg_path} ...")
    kg_tracks, kg_by_spotify, kg_by_norm_name = load_kaggle_tracks(kg_path)
    print(f"[INFO] Loaded {len(kg_tracks)} Kaggle tracks")

    print("[INFO] Matching Billboard rows to Kaggle tracks ...")
    matches = match_billboard_to_kaggle(bb_rows, kg_by_spotify, kg_by_norm_name)

    typical_cols = [
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
    ]
    if kg_tracks:
        kaggle_fields = list(kg_tracks[0].raw_row.keys())
    else:
        kaggle_fields = []
    numeric_feature_cols = [c for c in typical_cols if c in kaggle_fields]

    core_path = out_dir / f"spine_core_tracks_{args.version}.csv"
    audio_path = out_dir / f"spine_audio_spotify_{args.version}.csv"
    unmatched_path = out_dir / f"spine_unmatched_billboard_{args.version}.csv"
    summary_path = out_dir / f"historical_spine_build_{args.version}_summary.txt"

    print(f"[INFO] Writing core spine to {core_path} ...")
    write_spine_core_tracks(core_path, matches)

    print(f"[INFO] Writing audio features spine to {audio_path} ...")
    write_spine_audio_spotify(audio_path, matches, numeric_feature_cols)

    print(f"[INFO] Writing unmatched Billboard rows to {unmatched_path} ...")
    write_unmatched_billboard(unmatched_path, matches)

    summary = summarize(matches, numeric_feature_cols)
    print("")
    print(summary)

    with summary_path.open("w", encoding="utf-8") as f:
        f.write(summary + "\n")
    print(f"[INFO] Summary written to {summary_path}")


if __name__ == "__main__":
    main()
