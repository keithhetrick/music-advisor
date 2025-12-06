#!/usr/bin/env python3
"""
tools/hci_compare_targets.py

Compare local HCI_v1 outputs + audio features against the UT Austin
Billboard target CSV, and optionally offline Spotify/Kaggle audio
features.

For each matched track, this script can:
- Join local HCI_v1 + local .features.json.
- Join target labels (EchoTarget_v2, success_index_raw, etc.).
- Join "Spotify-like" features from an offline CSV (e.g. from Kaggle).
- Compute per-track drift metrics:
    * HCI_v1 vs EchoTarget_v2 (%)
    * HCI_v1 vs success_index_raw (%)
    * Tempo drift (local vs Spotify) in %
    * Duration drift (local vs Spotify) in %
    * Loudness difference (local LUFS - Spotify dB)
    * Danceability/Energy/Valence differences (local - Spotify)
- Write a wide CSV with all of the above.
- Optionally print drift summaries (like debug_spotify_drift.py)
  via the --summarize-drift flag.

Typical usage for a 1985–1986 Top 40 cohort:

  python tools/hci_compare_targets.py \
    --root features_output/2025/11/22 \
    --target-csv data/private/local_assets/hci_v2/hci_v2_targets_pop_us_1985_2024.csv \
    --spotify-features-csv calibration/spotify_offline/1985_1986/spotify_audio_features_1985_1986_20251122_185611.csv \
    --years 1985 1986 \
    --max-rank 40 \
    --tolerance-pct 15 \
    --out-dir calibration/comparisons/1985_1986 \
    --summarize-drift

This will:
- Print match + correlation summaries.
- Print drift summaries (if --summarize-drift).
- Write a CSV like:
    calibration/comparisons/1985_1986/hci_v1_vs_targets_1985_1986_YYYYMMDD_HHMMSS.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, Any, List, Optional, Sequence, Tuple, Set

from shared.config.paths import get_hci_v2_targets_csv


# ---------------------------------------------------------------------------
# Helpers: name normalization, safe parsing, correlations, summarization
# ---------------------------------------------------------------------------

def normalize_name(s: str) -> str:
    """
    Normalize artist/title names for fuzzy matching.

    - lowercase
    - '&' -> 'and'
    - strip quotes / apostrophes / backticks
    - remove parentheses
    - non-alphanumeric -> space
    - collapse whitespace
    - fix split contractions like 'don t' -> 'dont'
    """
    import re

    s = (s or "").lower()
    s = s.replace("&", "and")
    s = re.sub(r"[’'\"`]", "", s)
    s = re.sub(r"[()]", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _fix_contractions(s)
    return s


def _fix_contractions(norm: str) -> str:
    tokens = norm.split()
    out = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens):
            pair = (tokens[i], tokens[i + 1])

            if pair[0] in {
                "don", "can", "didn", "doesn",
                "isn", "wasn", "shouldn", "couldn",
                "wouldn", "ain"
            } and pair[1] == "t":
                out.append(pair[0] + "t")
                i += 2
                continue

            if pair == ("let", "s"):
                out.append("lets")
                i += 2
                continue

        out.append(tokens[i])
        i += 1

    return " ".join(out)


def safe_float(x) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def safe_int(x) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None


def pearson_r(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    n = len(xs)
    mx = mean(xs)
    my = mean(ys)
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    den_x = math.sqrt(sum((xs[i] - mx) ** 2 for i in range(n)))
    den_y = math.sqrt(sum((ys[i] - my) ** 2 for i in range(n)))
    if den_x <= 0.0 or den_y <= 0.0:
        return None
    return num / (den_x * den_y)


def summarize_metric(name: str, values: List[Optional[float]],
                     *, is_pct: bool = False, tol: Optional[float] = None) -> None:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        print(f"{name}: no data\n")
        return
    unit = " %" if is_pct else ""
    print(f"{name}:")
    print(f"  count  : {len(vals)}")
    print(f"  mean   : {mean(vals):.3f}{unit}")
    vals_sorted = sorted(vals)
    mid = len(vals_sorted) // 2
    if len(vals_sorted) % 2 == 0:
        med = (vals_sorted[mid - 1] + vals_sorted[mid]) / 2.0
    else:
        med = vals_sorted[mid]
    print(f"  median : {med:.3f}{unit}")
    print(f"  min    : {vals_sorted[0]:.3f}{unit}")
    print(f"  max    : {vals_sorted[-1]:.3f}{unit}")
    if tol is not None:
        pass_count = sum(1 for v in vals if abs(v) <= tol)
        pct = 100 * pass_count / len(vals)
        tol_unit = "%" if is_pct else ""
        print(f"  PASS   : {pass_count} / {len(vals)} "
              f"({pct:.1f}%) within ±{tol}{tol_unit}")
    print("")


# ---------------------------------------------------------------------------
# Dataclasses for structured storage
# ---------------------------------------------------------------------------

@dataclass
class TargetRow:
    key: str
    year: int
    artist: str
    title: str
    year_end_rank: Optional[int]
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LocalRow:
    key: str
    year: int
    artist_norm: str
    title_norm: str
    audio_file: str
    hci_score: Optional[float]
    hci_raw: Optional[float]
    axes: Dict[str, Optional[float]] = field(default_factory=dict)
    tempo_bpm: Optional[float] = None
    duration_sec: Optional[float] = None
    loudness_LUFS: Optional[float] = None
    danceability: Optional[float] = None
    energy: Optional[float] = None
    valence: Optional[float] = None


@dataclass
class SpotifyRow:
    key: str
    spotify_id: Optional[str]
    tempo: Optional[float]
    duration_sec: Optional[float]
    loudness: Optional[float]
    danceability: Optional[float]
    energy: Optional[float]
    valence: Optional[float]
    raw: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_targets(target_csv: Path,
                 years: Sequence[int],
                 max_rank: int) -> Tuple[Dict[str, TargetRow], List[str]]:
    years_set = set(years)
    targets: Dict[str, TargetRow] = {}

    with target_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            year = safe_int(row.get("year"))
            if year is None or year not in years_set:
                continue

            rank = safe_int(row.get("year_end_rank")
                            or row.get("year_end_position")
                            or row.get("rank"))
            if rank is None or rank > max_rank:
                continue

            artist = row.get("artist", "") or row.get("artists", "")
            title = row.get("title", "") or row.get("name", "")

            key = f"{year}|{normalize_name(artist)}|{normalize_name(title)}"

            targets[key] = TargetRow(
                key=key,
                year=year,
                artist=artist,
                title=title,
                year_end_rank=rank,
                raw=row,
            )

    print(f"[INFO] Loaded {len(targets)} target rows from {target_csv} "
          f"for years {sorted(years_set)} and rank <= {max_rank}")
    return targets, fieldnames


def load_local(root: Path,
               years: Sequence[int]) -> Tuple[Dict[str, LocalRow], Set[str]]:
    years_set = set(years)
    local: Dict[str, LocalRow] = {}
    all_axes: Set[str] = set()

    hci_files = sorted(root.rglob("*.hci.json"))
    print(f"[INFO] Found {len(hci_files)} local .hci.json files under {root}")

    for hci_path in hci_files:
        rel = hci_path.relative_to(root)
        parts = rel.parts
        if not parts:
            continue
        try:
            year = int(parts[0])
        except Exception:
            continue
        if year not in years_set:
            continue

        try:
            hci_blob = json.loads(hci_path.read_text())
        except Exception:
            continue

        # Extract HCI_v1 score + raw
        hci_score = None
        hci_raw = None
        axes_dict: Dict[str, Optional[float]] = {}

        if isinstance(hci_blob, dict):
            hci_block = hci_blob.get("HCI_v1")
            if isinstance(hci_block, dict):
                hci_score = safe_float(hci_block.get("score"))
                hci_raw = safe_float(hci_block.get("raw"))
                axes_src = hci_block.get("axes") or hci_blob.get("axes")
            else:
                axes_src = hci_blob.get("axes")
            if isinstance(axes_src, dict):
                for k, v in axes_src.items():
                    if isinstance(v, (int, float)):
                        axes_dict[k] = float(v)
                    else:
                        axes_dict[k] = None
                    all_axes.add(k)

        # Infer artist/title from slug_dir
        slug_dir = hci_path.parent.name
        slug_parts = slug_dir.split("__")
        if len(slug_parts) < 2:
            continue
        year_artist = slug_parts[0]  # e.g. "1985_a_ha"
        title_slug = slug_parts[1]   # e.g. "take_on_me"

        artist_bits = year_artist.split("_")[1:]  # drop year
        artist_slug = " ".join(artist_bits)
        title_name = title_slug.replace("_", " ")

        artist_norm = normalize_name(artist_slug)
        title_norm = normalize_name(title_name)

        key = f"{year}|{artist_norm}|{title_norm}"

        # Load neighbor .features.json
        features = {}
        # Strategy:
        # 1) Try non-timestamped strict name: <stem_core>.features.json
        # 2) Fallback to timestamped pattern: <stem_core>_*.features.json
        stem = hci_path.stem  # e.g. "1985_a_ha__take_on_me__single.hci"
        if stem.endswith(".hci"):
            stem_core = stem[:-4]
        else:
            stem_core = stem

        strict_feat_name = stem_core + ".features.json"
        strict_feat_path = hci_path.with_name(strict_feat_name)

        if strict_feat_path.exists():
            try:
                features = json.loads(strict_feat_path.read_text())
            except Exception:
                features = {}
        else:
            candidates = sorted(hci_path.parent.glob(f"{stem_core}_*.features.json"))
            if candidates:
                feat_path = candidates[-1]
                try:
                    features = json.loads(feat_path.read_text())
                except Exception:
                    features = {}

        # Features may be flat or wrapped
        if isinstance(features, dict) and "features_full" in features:
            feats = features.get("features_full") or {}
        else:
            feats = features if isinstance(features, dict) else {}

        tempo_bpm = safe_float(feats.get("tempo_bpm"))
        duration_sec = safe_float(feats.get("duration_sec"))
        loudness_LUFS = safe_float(feats.get("loudness_LUFS"))
        danceability = safe_float(feats.get("danceability"))
        energy = safe_float(feats.get("energy"))
        valence = safe_float(feats.get("valence"))

        local[key] = LocalRow(
            key=key,
            year=year,
            artist_norm=artist_norm,
            title_norm=title_norm,
            audio_file=str(hci_path),
            hci_score=hci_score,
            hci_raw=hci_raw,
            axes=axes_dict,
            tempo_bpm=tempo_bpm,
            duration_sec=duration_sec,
            loudness_LUFS=loudness_LUFS,
            danceability=danceability,
            energy=energy,
            valence=valence,
        )

    print(f"[INFO] Local rows after year filter: {len(local)}")
    return local, all_axes


def load_spotify_features(spotify_csv: Path,
                          years: Sequence[int]) -> Dict[str, SpotifyRow]:
    years_set = set(years)
    spotify: Dict[str, SpotifyRow] = {}

    with spotify_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = safe_int(row.get("year"))
            if year is None or year not in years_set:
                continue

            artist = row.get("artist", "") or row.get("artists", "")
            title = row.get("title", "") or row.get("name", "")
            key = f"{year}|{normalize_name(artist)}|{normalize_name(title)}"

            tempo = safe_float(row.get("tempo"))
            loudness = safe_float(row.get("loudness"))
            danceability = safe_float(row.get("danceability"))
            energy = safe_float(row.get("energy"))
            valence = safe_float(row.get("valence"))

            duration_sec = None
            dur_ms = safe_float(row.get("duration_ms"))
            dur_sec_col = safe_float(row.get("duration_sec"))
            if dur_sec_col is not None:
                duration_sec = dur_sec_col
            elif dur_ms is not None:
                duration_sec = dur_ms / 1000.0

            spotify_id = row.get("spotify_id") or row.get("id") or None

            spotify[key] = SpotifyRow(
                key=key,
                spotify_id=spotify_id,
                tempo=tempo,
                duration_sec=duration_sec,
                loudness=loudness,
                danceability=danceability,
                energy=energy,
                valence=valence,
                raw=row,
            )

    print(f"[INFO] Loaded {len(spotify)} Spotify rows from {spotify_csv} "
          f"for years {sorted(years_set)}")
    return spotify


# ---------------------------------------------------------------------------
# Main comparison + CSV writing
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Compare local HCI_v1 outputs + features against UT target CSV "
            "and optionally offline Spotify/Kaggle audio features."
        )
    )
    ap.add_argument(
        "--root",
        required=True,
        help="Root of local features/HCI tree (e.g. features_output/2025/11/22)",
    )
    ap.add_argument(
        "--target-csv",
        required=True,
        help=f"UT Austin-based targets CSV (e.g. {get_hci_v2_targets_csv()})",
    )
    ap.add_argument(
        "--spotify-features-csv",
        help="Optional offline Spotify/Kaggle features CSV to join on "
             "(e.g. calibration/spotify_offline/.../spotify_audio_features_*.csv)",
    )
    ap.add_argument(
        "--years",
        nargs="+",
        type=int,
        required=True,
        help="Years to include (e.g. 1985 1986)",
    )
    ap.add_argument(
        "--max-rank",
        type=int,
        default=40,
        help="Max year_end_rank to include from target CSV (default: 40)",
    )
    ap.add_argument(
        "--tolerance-pct",
        type=float,
        default=15.0,
        help="Tolerance in % for HCI_v1 vs EchoTarget_v2 PASS/FAIL (default: 15.0)",
    )
    ap.add_argument(
        "--out-dir",
        help="Output directory for comparison CSV. If omitted, will use "
             "calibration/comparisons/<years_label>",
    )
    ap.add_argument(
        "--summarize-drift",
        action="store_true",
        help="If set, print drift summaries (tempo, loudness, dance/energy/valence, label drift).",
    )
    args = ap.parse_args()

    root = Path(args.root)
    target_csv = Path(args.target_csv)
    spotify_csv = Path(args.spotify_features_csv) if args.spotify_features_csv else None
    years = sorted(set(args.years))

    if not root.exists():
        raise SystemExit(f"[ERROR] root does not exist: {root}")
    if not target_csv.exists():
        raise SystemExit(f"[ERROR] target-csv does not exist: {target_csv}")
    if spotify_csv and not spotify_csv.exists():
        raise SystemExit(f"[ERROR] spotify-features-csv does not exist: {spotify_csv}")

    # ----------------------------------------------------------------------
    # 1) Load data: targets, local, Spotify
    # ----------------------------------------------------------------------
    targets, target_fieldnames = load_targets(target_csv, years, args.max_rank)
    local, all_axes = load_local(root, years)
    if spotify_csv:
        spotify = load_spotify_features(spotify_csv, years)
    else:
        spotify = {}

    keys_targets = set(targets.keys())
    keys_local = set(local.keys())
    keys_spotify = set(spotify.keys())

    matched = sorted(keys_targets & keys_local)
    local_only = sorted(keys_local - keys_targets)
    target_only = sorted(keys_targets - keys_local)

    print("")
    print("=== MATCH SUMMARY (Local HCI vs Targets) ===")
    print(f"Matched songs      : {len(matched)}")
    print(f"Local-only (.hci)  : {len(local_only)}")
    print(f"Target-only (CSV)  : {len(target_only)}")
    print("")

    # ----------------------------------------------------------------------
    # 2) Correlations: HCI vs labels
    # ----------------------------------------------------------------------
    hci_vals_for_et: List[float] = []
    et_vals: List[float] = []

    hci_vals_for_si: List[float] = []
    si_vals: List[float] = []

    hci_vals_for_rank: List[float] = []
    inv_rank_vals: List[float] = []

    for key in matched:
        loc = local[key]
        tgt = targets[key]

        if loc.hci_score is None:
            continue

        hci_score = loc.hci_score

        # EchoTarget_v2
        et = safe_float(tgt.raw.get("EchoTarget_v2"))
        if et is not None:
            hci_vals_for_et.append(hci_score)
            et_vals.append(et)

        # success_index_raw
        si = safe_float(tgt.raw.get("success_index_raw"))
        if si is not None:
            hci_vals_for_si.append(hci_score)
            si_vals.append(si)

        # inverted rank
        if tgt.year_end_rank is not None:
            inv_rank = args.max_rank + 1 - tgt.year_end_rank
            hci_vals_for_rank.append(hci_score)
            inv_rank_vals.append(float(inv_rank))

    print("=== CORRELATIONS (on matched songs only) ===")
    r_et = pearson_r(hci_vals_for_et, et_vals)
    if r_et is not None:
        print(f"\nHCI_v1 score vs EchoTarget_v2:\n r = {r_et:.3f} (n={len(hci_vals_for_et)})")
    else:
        print("\nHCI_v1 score vs EchoTarget_v2:\n r = N/A")

    r_si = pearson_r(hci_vals_for_si, si_vals)
    if r_si is not None:
        print(f"\nHCI_v1 score vs success_index_raw:\n r = {r_si:.3f} (n={len(hci_vals_for_si)})")
    else:
        print("\nHCI_v1 score vs success_index_raw:\n r = N/A")

    r_rank = pearson_r(hci_vals_for_rank, inv_rank_vals)
    if r_rank is not None:
        print(
            f"\nHCI_v1 score vs inverted year_end_rank ({args.max_rank + 1} - rank):\n "
            f"r = {r_rank:.3f} (n={len(hci_vals_for_rank)})"
        )
    else:
        print("\nHCI_v1 score vs inverted year_end_rank:\n r = N/A")

    print("")

    # ----------------------------------------------------------------------
    # 3) Build wide CSV rows
    # ----------------------------------------------------------------------
    years_label = "_".join(str(y) for y in years)
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = Path("calibration") / "comparisons" / years_label
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = out_dir / f"hci_v1_vs_targets_{years_label}_{timestamp}.csv"

    axis_names = sorted(all_axes)

    # We will prefix all target fields with meta_
    meta_fields = [f"meta_{name}" for name in (target_fieldnames or [])]

    base_cols = [
        "audio_file",
        "local_year",
        "local_artist_slug",
        "local_title_slug",
        "HCI_v1_score",
        "HCI_v1_raw",
    ]
    axis_cols = [f"HCI_axis_{ax}" for ax in axis_names]
    feat_cols = [
        "feat_tempo_bpm",
        "feat_duration_sec",
        "feat_loudness_LUFS",
        "feat_danceability",
        "feat_energy",
        "feat_valence",
    ]
    spotify_cols = [
        "spotify_id",
        "spotify_tempo",
        "spotify_duration_sec",
        "spotify_loudness",
        "spotify_danceability",
        "spotify_energy",
        "spotify_valence",
    ]
    drift_cols = [
        "tempo_drift_pct",
        "duration_drift_pct",
        "loudness_diff_db",
        "danceability_diff",
        "energy_diff",
        "valence_diff",
        "drift_pct_vs_EchoTarget_v2",
        "drift_pct_vs_success_index_raw",
        "drift_pass_fail_vs_EchoTarget_v2",
    ]

    fieldnames = base_cols + axis_cols + feat_cols + spotify_cols + drift_cols + meta_fields

    # For drift summaries if requested
    tempo_drift_vals: List[Optional[float]] = []
    duration_drift_vals: List[Optional[float]] = []
    loudness_diff_vals: List[Optional[float]] = []
    dance_diff_vals: List[Optional[float]] = []
    energy_diff_vals: List[Optional[float]] = []
    valence_diff_vals: List[Optional[float]] = []
    drift_et_vals: List[Optional[float]] = []
    drift_si_vals: List[Optional[float]] = []

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for key in matched:
            loc = local[key]
            tgt = targets[key]
            sp = spotify.get(key)

            row: Dict[str, Any] = {}

            # Base
            row["audio_file"] = loc.audio_file
            row["local_year"] = loc.year
            row["local_artist_slug"] = loc.artist_norm
            row["local_title_slug"] = loc.title_norm
            row["HCI_v1_score"] = loc.hci_score
            row["HCI_v1_raw"] = loc.hci_raw

            # Axes
            for ax in axis_names:
                row[f"HCI_axis_{ax}"] = loc.axes.get(ax)

            # Local features
            row["feat_tempo_bpm"] = loc.tempo_bpm
            row["feat_duration_sec"] = loc.duration_sec
            row["feat_loudness_LUFS"] = loc.loudness_LUFS
            row["feat_danceability"] = loc.danceability
            row["feat_energy"] = loc.energy
            row["feat_valence"] = loc.valence

            # Target label drift
            et = safe_float(tgt.raw.get("EchoTarget_v2"))
            si = safe_float(tgt.raw.get("success_index_raw"))
            hci_score = loc.hci_score

            drift_et = None
            drift_si = None
            drift_pass = "N/A"

            if hci_score is not None and et is not None and et != 0.0:
                drift_et = (hci_score - et) / et * 100.0
                drift_et_vals.append(drift_et)
                if abs(drift_et) <= args.tolerance_pct:
                    drift_pass = "PASS"
                else:
                    drift_pass = "FAIL"
            else:
                drift_et_vals.append(None)

            if hci_score is not None and si is not None and si != 0.0:
                drift_si = (hci_score - si) / si * 100.0
                drift_si_vals.append(drift_si)
            else:
                drift_si_vals.append(None)

            row["drift_pct_vs_EchoTarget_v2"] = drift_et
            row["drift_pct_vs_success_index_raw"] = drift_si
            row["drift_pass_fail_vs_EchoTarget_v2"] = drift_pass

            # Spotify fields + drift (if available)
            tempo_drift = None
            duration_drift = None
            loud_diff = None
            dance_diff = None
            energy_diff = None
            valence_diff = None

            if sp is not None:
                row["spotify_id"] = sp.spotify_id
                row["spotify_tempo"] = sp.tempo
                row["spotify_duration_sec"] = sp.duration_sec
                row["spotify_loudness"] = sp.loudness
                row["spotify_danceability"] = sp.danceability
                row["spotify_energy"] = sp.energy
                row["spotify_valence"] = sp.valence

                # Tempo drift %
                if loc.tempo_bpm is not None and sp.tempo not in (None, 0.0):
                    tempo_drift = (loc.tempo_bpm - sp.tempo) / sp.tempo * 100.0

                # Duration drift %
                if loc.duration_sec is not None and sp.duration_sec not in (None, 0.0):
                    duration_drift = (loc.duration_sec - sp.duration_sec) / sp.duration_sec * 100.0

                # Loudness diff (local LUFS - Spotify dB)
                if loc.loudness_LUFS is not None and sp.loudness is not None:
                    loud_diff = loc.loudness_LUFS - sp.loudness

                # Danceability / Energy / Valence
                if loc.danceability is not None and sp.danceability is not None:
                    dance_diff = loc.danceability - sp.danceability
                if loc.energy is not None and sp.energy is not None:
                    energy_diff = loc.energy - sp.energy
                if loc.valence is not None and sp.valence is not None:
                    valence_diff = loc.valence - sp.valence

            row["tempo_drift_pct"] = tempo_drift
            row["duration_drift_pct"] = duration_drift
            row["loudness_diff_db"] = loud_diff
            row["danceability_diff"] = dance_diff
            row["energy_diff"] = energy_diff
            row["valence_diff"] = valence_diff

            tempo_drift_vals.append(tempo_drift)
            duration_drift_vals.append(duration_drift)
            loudness_diff_vals.append(loud_diff)
            dance_diff_vals.append(dance_diff)
            energy_diff_vals.append(energy_diff)
            valence_diff_vals.append(valence_diff)

            # Meta target fields
            for name in target_fieldnames or []:
                row[f"meta_{name}"] = tgt.raw.get(name)

            writer.writerow(row)

    print(f"[OK] Wrote {len(matched)} rows to {out_csv}")
    print("")

    # ----------------------------------------------------------------------
    # 4) Optional drift summaries (local vs Spotify + label drift)
    # ----------------------------------------------------------------------
    if args.summarize_drift:
        print("=== DRIFT SUMMARY (Local vs Spotify + Labels) ===\n")

        # Tunable/implicit tolerances for this summary
        TEMPO_TOL_PCT = 5.0
        DURATION_TOL_PCT = 2.0
        LOUDNESS_TOL_DB = 2.0
        METRIC_TOL = 0.10

        summarize_metric(
            "Tempo drift (local tempo_bpm vs Spotify tempo)",
            tempo_drift_vals,
            is_pct=True,
            tol=TEMPO_TOL_PCT,
        )

        summarize_metric(
            "Duration drift (local duration_sec vs Spotify duration_sec)",
            duration_drift_vals,
            is_pct=True,
            tol=DURATION_TOL_PCT,
        )

        summarize_metric(
            "Loudness difference (local LUFS - Spotify dB)",
            loudness_diff_vals,
            is_pct=False,
            tol=LOUDNESS_TOL_DB,
        )

        summarize_metric(
            "Danceability difference (local - Spotify)",
            dance_diff_vals,
            is_pct=False,
            tol=METRIC_TOL,
        )

        summarize_metric(
            "Energy difference (local - Spotify)",
            energy_diff_vals,
            is_pct=False,
            tol=METRIC_TOL,
        )

        summarize_metric(
            "Valence difference (local - Spotify)",
            valence_diff_vals,
            is_pct=False,
            tol=METRIC_TOL,
        )

        summarize_metric(
            f"HCI_v1 vs EchoTarget_v2 drift (%, tolerance={args.tolerance_pct}%)",
            drift_et_vals,
            is_pct=True,
            tol=args.tolerance_pct,
        )

        summarize_metric(
            "HCI_v1 vs success_index_raw drift (%)",
            drift_si_vals,
            is_pct=True,
            tol=None,
        )


if __name__ == "__main__":
    main()
