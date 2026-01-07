#!/usr/bin/env python3
"""
hci_echo_probe_from_spine_v1.py

Given a WIP features JSON, probe the Tier 1 Historical Spine (v1)
stored in data/private/local_assets/historical_echo/historical_echo.db (by default) and report the
closest historical neighbors + a simple echo summary.

Usage (from repo root):

  python tools/hci_echo_probe_from_spine_v1.py \
    --features path/to/track.features.json \
    --top-k 10 \
    --year-max 2020

You can override DB path, year range, top-k neighbors, etc. via flags.

This file also exposes a programmatic API:

  run_echo_probe_for_features(...)

which can be imported and called from the .client.rich.txt builder so that
the historical echo info is embedded automatically in the client injection.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Tuple

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from shared.config.paths import get_historical_echo_db_path
from tools.audio.spine.spine_slug import make_spine_slug
from tools.external.acousticbrainz_utils import compact_to_probe_axes, load_compact_from_json


# ---------------------------------------------------------------------------
# CLI ARG PARSER
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Historical echo probe against Tier 1 spine v1."
    )
    p.add_argument(
        "--features",
        required=True,
        help="Path to WIP .features.json file.",
    )
    p.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help="Path to historical_echo SQLite DB (default honors MA_DATA_ROOT).",
    )
    p.add_argument(
        "--tiers",
        default="tier1_modern",
        help=(
            "Comma list of tiers to search (default: tier1_modern). "
            "Supported: tier1_modern, tier2_modern, tier3_modern. "
            "If set, overrides --table/--echo-tier to the canonical values for that tier."
        ),
    )
    p.add_argument(
        "--table",
        default="spine_master_v1_lanes",
        help="Spine table name (default: spine_master_v1_lanes).",
    )
    p.add_argument(
        "--echo-tier",
        default="EchoTier_1_YearEnd_Top40",
        help="Echo tier filter (default: EchoTier_1_YearEnd_Top40).",
    )
    p.add_argument(
        "--year-min",
        type=int,
        default=1985,
        help="Minimum year to include from spine (default: 1985).",
    )
    p.add_argument(
        "--year-max",
        type=int,
        default=2020,
        help="Maximum year to include from spine (default: 2020; newer years are sparse).",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of nearest neighbors to report (default: 10).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra debug info.",
    )
    p.add_argument(
        "--use-acousticbrainz-fallback",
        action="store_true",
        help="Allow Tier 3 neighbors to fall back to AcousticBrainz features when Essentia is missing.",
    )
    p.add_argument(
        "--acousticbrainz-max-fallback",
        type=int,
        default=0,
        help="Cap how many Tier 3 rows can use AcousticBrainz fallback (0 = no cap).",
    )
    p.add_argument(
        "--use-tempo-confidence",
        action="store_true",
        help="Down-weight tempo axis when WIP tempo confidence is low (non-destructive; default off).",
    )
    p.add_argument(
        "--tempo-confidence-threshold",
        type=float,
        default=0.4,
        help="Confidence score below which tempo is down-weighted (default: 0.4).",
    )
    p.add_argument(
        "--tempo-weight-low",
        type=float,
        default=0.3,
        help="Weight multiplier for tempo axis when confidence is low (default: 0.3).",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# WIP FEATURE LOADING
# ---------------------------------------------------------------------------


def _pick_field(data: Dict[str, Any], name: str, candidates: List[str]) -> float | None:
    """
    Try to select a numeric field from a JSON dict.

    1) Prefer explicit candidate keys (exact match).
    2) Fallback: fuzzy search for keys containing the name token.
    """
    # 1) Exact candidate keys first
    for key in candidates:
        if key in data and data[key] is not None:
            try:
                return float(data[key])
            except (TypeError, ValueError):
                continue

    # 2) Fuzzy fallback: any numeric field containing the token
    token = name.lower()
    for key, value in data.items():
        if token in key.lower() and isinstance(value, (int, float)):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue

    return None


def load_wip_features(path: Path) -> Dict[str, float]:
    """
    Load a WIP .features.json and extract core audio dimensions:

      - tempo (bpm)
      - energy
      - valence
      - loudness (LUFS or similar)

    This is intentionally forgiving re: field names.
    """
    if not path.is_file():
        raise FileNotFoundError(f"WIP features file not found: {path}")

    data = json.loads(path.read_text())

    tempo = _pick_field(
        data,
        "tempo",
        [
            "tempo",
            "tempo_bpm",
            "estimated_tempo",
            "tempo_estimate_bpm",
            "tempo_global",
            "tempo_mean",
        ],
    )
    energy = _pick_field(
        data,
        "energy",
        [
            "energy",
            "rms_energy",
            "energy_mean",
            "energy_global",
        ],
    )
    valence = _pick_field(
        data,
        "valence",
        [
            "valence",
            "valence_mean",
            "valence_global",
        ],
    )
    loudness = _pick_field(
        data,
        "loudness",
        [
            "loudness_LUFS",
            "loudness",
            "integrated_LUFS",
            "loudness_integrated",
        ],
    )
    tempo_conf_score = _pick_field(
        data,
        "tempo_confidence_score",
        [
            "tempo_confidence_score",
            "tempo_confidence",
        ],
    )

    missing: List[str] = []
    if tempo is None:
        missing.append("tempo*")
    if energy is None:
        missing.append("energy*")
    if valence is None:
        missing.append("valence*")
    if loudness is None:
        missing.append("loudness*")

    if missing:
        keys_preview = ", ".join(sorted(data.keys()))
        raise ValueError(
            "WIP features file is missing required fields or recognizable variants: "
            + ", ".join(missing)
            + f"\nFile: {path}\nAvailable keys: {keys_preview}"
        )

    return {
        "tempo": tempo,
        "energy": energy,
        "valence": valence,
        "loudness": loudness,
        "tempo_confidence_score": tempo_conf_score,
    }


# ---------------------------------------------------------------------------
# DB ACCESS + SPINE LOADING
# ---------------------------------------------------------------------------


def connect_db(db_path: Path) -> sqlite3.Connection:
    """
    Connect to the historical_echo DB.

    If db_path is relative (e.g. 'data/historical_echo/historical_echo.db'),
    resolve it relative to the repo root (parent of the 'tools' directory),
    so this works both from CLI and from Automator where the CWD can differ.
    """
    # If not absolute, treat as relative to repo root (…/music-advisor)
    if not db_path.is_absolute():
        repo_root = Path(__file__).resolve().parents[1]
        db_path = repo_root / db_path

    if not db_path.is_file():
        raise FileNotFoundError(f"SQLite DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def load_spine_rows(
    conn: sqlite3.Connection,
    table: str,
    echo_tier: str,
    year_min: int,
    year_max: int,
    tier_label: str,
    feature_source: str = "essentia_local",
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Load Tier 1 rows with usable audio from the spine table.
    All audio / lane columns are stored as TEXT in SQLite, so
    we cast to float and skip anything that fails.
    """
    q = f"""
        SELECT
          spine_track_id,
          year,
          artist,
          title,
          tempo,
          valence,
          energy,
          loudness,
          tempo_band,
          valence_band,
          energy_band
        FROM {table}
        WHERE echo_tier = ?
          AND has_audio = '1'
          AND CAST(year AS INTEGER) BETWEEN ? AND ?
          AND tempo <> ''
          AND valence <> ''
          AND energy <> ''
          AND loudness <> ''
    """
    cur = conn.execute(q, (echo_tier, year_min, year_max))
    rows: List[Dict[str, Any]] = []

    for row in cur:
        try:
            tempo = float(row["tempo"])
            valence = float(row["valence"])
            energy = float(row["energy"])
            loudness = float(row["loudness"])
            year_val = int(row["year"])
        except (TypeError, ValueError):
            # Skip malformed rows
            continue

        rows.append(
            {
                "spine_track_id": row["spine_track_id"],
                "year": year_val,
                "artist": row["artist"],
                "title": row["title"],
                "tempo": tempo,
                "valence": valence,
                "energy": energy,
                "loudness": loudness,
                "tempo_band": row["tempo_band"],
                "valence_band": row["valence_band"],
                "energy_band": row["energy_band"],
                "tier": tier_label,
                "slug": make_spine_slug(row["title"], row["artist"]),
                "feature_source": feature_source,
            }
        )

    if verbose:
        print(
            f"[echo_probe] Loaded {len(rows)} spine rows with usable audio "
            f"({year_min}–{year_max}, tier={echo_tier})"
        )
    return rows


def merge_rows_prefer_highest_tier(
    rows: List[Dict[str, Any]],
    tier_priority: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Deduplicate by slug, preferring the highest-priority tier (tier1 > tier2 > tier3).
    This ensures the same song does not appear multiple times across tiers.
    """
    tier_priority = tier_priority or ["tier1_modern", "tier2_modern", "tier3_modern"]
    rank = {t: i for i, t in enumerate(tier_priority)}

    best: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        slug = r.get("slug") or make_spine_slug(r.get("title", ""), r.get("artist", ""))
        tier = r.get("tier", "tier1_modern")
        current_rank = rank.get(tier, len(rank))

        if slug not in best:
            best[slug] = r
            continue

        prev = best[slug]
        prev_rank = rank.get(prev.get("tier", "tier1_modern"), len(rank))
        if current_rank < prev_rank:
            best[slug] = r

    return list(best.values())


# ---------------------------------------------------------------------------
# ACOUSTICBRAINZ FALLBACK HELPERS (TIER 3 ONLY)
# ---------------------------------------------------------------------------


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def load_acousticbrainz_feature_map(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """
    Load compact AcousticBrainz feature blobs keyed by slug.
    Safe to call even if the table is absent.
    """
    if not table_exists(conn, "features_external_acousticbrainz_v1"):
        return {}
    cur = conn.execute("SELECT slug, features_json FROM features_external_acousticbrainz_v1")
    feat_map: Dict[str, Dict[str, Any]] = {}
    for slug, features_json in cur.fetchall():
        try:
            feat_map[slug] = load_compact_from_json(features_json)
        except Exception:
            continue
    return feat_map


def band_tempo(tempo: float | None) -> str:
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


def band_valence(valence: float | None) -> str:
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


def band_energy(energy: float | None) -> str:
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


def band_loudness(loudness: float | None) -> str:
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


def load_tier3_acousticbrainz_rows(
    conn: sqlite3.Connection,
    year_min: int,
    year_max: int,
    echo_tier: str,
    ab_features: Dict[str, Dict[str, Any]],
    max_fallback: int | None = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Build Tier 3 rows from AcousticBrainz compact features when Essentia is missing.
    """
    if not ab_features or not table_exists(conn, "spine_master_tier3_modern_lanes_v1"):
        return []

    cur = conn.execute(
        """
        SELECT spine_track_id, slug, title, artist, year, has_audio, audio_features_path
        FROM spine_master_tier3_modern_lanes_v1
        WHERE echo_tier = ?
          AND CAST(year AS INTEGER) BETWEEN ? AND ?
        """,
        (echo_tier, year_min, year_max),
    )
    rows: List[Dict[str, Any]] = []

    for (
        spine_track_id,
        slug,
        title,
        artist,
        year,
        has_audio,
        audio_features_path,
    ) in cur.fetchall():
        slug_val = (slug or "").strip() or make_spine_slug(title or "", artist or "")

        has_audio_flag = str(has_audio or "").strip() == "1"
        audio_path = (audio_features_path or "").strip()
        if has_audio_flag and audio_path:
            # Prefer local Essentia when present
            continue

        compact = ab_features.get(slug_val)
        if not compact:
            continue
        axes = compact_to_probe_axes(compact)
        if not axes:
            continue

        try:
            year_val = int(str(year).strip())
        except (TypeError, ValueError):
            continue

        rows.append(
            {
                "spine_track_id": spine_track_id,
                "year": year_val,
                "artist": artist,
                "title": title,
                "tempo": axes["tempo"],
                "valence": axes["valence"],
                "energy": axes["energy"],
                "loudness": axes["loudness"],
                "tempo_band": band_tempo(axes["tempo"]),
                "valence_band": band_valence(axes["valence"]),
                "energy_band": band_energy(axes["energy"]),
                "loudness_band": band_loudness(axes["loudness"]),
                "tier": "tier3_modern",
                "slug": slug_val,
                "feature_source": "acousticbrainz",
            }
        )

        if max_fallback and len(rows) >= max_fallback:
            break

    if verbose:
        print(f"[echo_probe] AcousticBrainz fallback rows added: {len(rows)}")
    return rows


# ---------------------------------------------------------------------------
# STATS + DISTANCE
# ---------------------------------------------------------------------------


def zscore(x: float, mu: float, sigma: float) -> float:
    if sigma == 0 or sigma is None:
        return 0.0
    return (x - mu) / sigma


def compute_feature_stats(rows: List[Dict[str, Any]]) -> Dict[str, Tuple[float, float]]:
    tempos = [r["tempo"] for r in rows]
    vals = [r["valence"] for r in rows]
    eners = [r["energy"] for r in rows]
    louds = [r["loudness"] for r in rows]

    stats = {
        "tempo": (mean(tempos), pstdev(tempos) if len(tempos) > 1 else 0.0),
        "valence": (mean(vals), pstdev(vals) if len(vals) > 1 else 0.0),
        "energy": (mean(eners), pstdev(eners) if len(eners) > 1 else 0.0),
        "loudness": (mean(louds), pstdev(louds) if len(louds) > 1 else 0.0),
    }
    return stats


def compute_distance(
    wip: Dict[str, float],
    spine_row: Dict[str, float],
    stats: Dict[str, Tuple[float, float]],
    use_tempo_conf: bool = False,
    tempo_conf_score: float | None = None,
    tempo_conf_threshold: float = 0.4,
    tempo_weight_low: float = 0.3,
) -> float:
    """
    Simple z-scored Euclidean distance across (tempo, valence, energy, loudness).

    Each dimension is z-scored using Tier 1 stats so that we are comparing
    relative positions in the distribution, not raw scales.
    """
    dims = ["tempo", "valence", "energy", "loudness"]
    dist_sq = 0.0
    for d in dims:
        mu, sigma = stats[d]
        z_wip = zscore(wip[d], mu, sigma)
        z_spine = zscore(spine_row[d], mu, sigma)
        diff = z_wip - z_spine
        weight = 1.0
        if use_tempo_conf and d == "tempo":
            if tempo_conf_score is not None and tempo_conf_score < tempo_conf_threshold:
                weight = tempo_weight_low
        dist_sq += weight * diff * diff
    return math.sqrt(dist_sq)


def tier_priority(label: str) -> int:
    """Lower is higher priority for dedupe."""
    order = {
        "tier1_modern": 0,
        "tier2_modern": 1,
        "tier3_modern": 2,
    }
    return order.get(label, 99)


def select_top_neighbors(rows: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """
    Sort by (tier priority, distance) and dedupe by slug (title+artist) so
    the same song doesn't appear multiple times across tiers.
    """
    # Group by tier (sorted by priority), keep each tier sorted by distance,
    # then interleave tiers so tier2/tier3 can surface even when tier1 is dense.
    rows_by_tier: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        tier = r.get("tier", "tier1_modern")
        rows_by_tier.setdefault(tier, []).append(r)

    for tier, items in rows_by_tier.items():
        items.sort(key=lambda r: r.get("distance", float("inf")))

    tier_order = sorted(rows_by_tier.keys(), key=tier_priority)
    seen = set()
    selected: List[Dict[str, Any]] = []

    # Round-robin across tiers until we either exhaust data or hit top_k.
    while len(selected) < top_k and any(rows_by_tier.values()):
        progress = False
        for tier in tier_order:
            tier_list = rows_by_tier.get(tier, [])
            while tier_list and len(selected) < top_k:
                cand = tier_list.pop(0)
                key = make_spine_slug(cand["title"], cand["artist"])
                if key in seen:
                    continue
                seen.add(key)
                selected.append(cand)
                progress = True
                break
        if not progress:
            break

    return selected


# ---------------------------------------------------------------------------
# PRESENTATION HELPERS
# ---------------------------------------------------------------------------


def bucket_decade(year: int) -> str:
    if 1985 <= year <= 1994:
        return "1985–1994"
    if 1995 <= year <= 2004:
        return "1995–2004"
    if 2005 <= year <= 2014:
        return "2005–2014"
    if 2015 <= year <= 2024:
        return "2015–2024"
    return "other"


def summarize_neighbors(neighbors: List[Dict[str, Any]]) -> None:
    decade_counts: Dict[str, int] = {}
    for n in neighbors:
        dec = bucket_decade(n["year"])
        decade_counts[dec] = decade_counts.get(dec, 0) + 1

    print("\n== Echo Summary ==")
    if not neighbors:
        print("No neighbors found.")
        return

    for dec, count in sorted(decade_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"- {dec}: {count} neighbor(s) in top-k")

    print("\nLane snapshot from top neighbors:")
    for n in neighbors[:5]:
        print(
            f"  • {n['year']} – {n['artist']} — {n['title']} "
            f"[tempo={n['tempo_band']}, valence={n['valence_band']}, energy={n['energy_band']}]"
        )


def print_neighbors(
    wip_features: Dict[str, float],
    neighbors: List[Dict[str, Any]],
) -> None:
    print("== WIP Features (raw) ==")
    print(
        f"tempo={wip_features['tempo']:.2f} bpm, "
        f"valence={wip_features['valence']:.3f}, "
        f"energy={wip_features['energy']:.3f}, "
        f"loudness={wip_features['loudness']:.2f}"
    )

    if not neighbors:
        print("\nNo neighbors found in Tier 1 spine with usable audio.")
        return

    tier_labels = sorted({n.get("tier", "tier1_modern") for n in neighbors})
    tier_label_str = ",".join(tier_labels)
    print(f"\n== Nearest Historical Neighbors (tiers: {tier_label_str}) ==")
    header = (
        f"{'#':>2}  {'dist':>7}  {'tier':<10}  {'src':<12}  {'year':>4}  "
        f"{'artist':<25}  {'title':<40}  {'tempo':>6}  {'val':>5}  {'eng':>5}"
    )
    print(header)
    print("-" * len(header))

    for idx, n in enumerate(neighbors, start=1):
        print(
            f"{idx:>2}  "
            f"{n['distance']:.3f}  "
            f"{n.get('tier',''):10.10}  "
            f"{n.get('feature_source',''):12.12}  "
            f"{n['year']:>4}  "
            f"{n['artist'][:25]:<25}  "
            f"{n['title'][:40]:<40}  "
            f"{n['tempo']:>6.1f}  "
            f"{n['valence']:>5.3f}  "
            f"{n['energy']:>5.3f}"
        )


# ---------------------------------------------------------------------------
# PROGRAMMATIC API (for .client.rich.txt builder)
# ---------------------------------------------------------------------------


def run_echo_probe_for_features(
    features_path: str,
    db: str = "data/historical_echo/historical_echo.db",
    table: str = "spine_master_v1_lanes",
    echo_tier: str = "EchoTier_1_YearEnd_Top40",
    year_min: int = 1985,
    year_max: int = 2020,
    top_k: int = 10,
    tiers: str | None = None,
    use_acousticbrainz_fallback: bool = False,
    acousticbrainz_max_fallback: int | None = None,
    use_tempo_confidence: bool = False,
    tempo_confidence_threshold: float = 0.4,
    tempo_weight_low: float = 0.3,
) -> Dict[str, Any]:
    """
    Programmatic API: given a WIP .features.json, return a dict with:

      - 'wip_features': {tempo, energy, valence, loudness}
      - 'neighbors': [ {year, artist, title, tempo, valence, energy, loudness,
                        tempo_band, valence_band, energy_band, distance, feature_source}, ... ]
      - 'decade_counts': { '1985–1994': N, ... }

    Safe to call from the .client.rich.txt builder. Does not print.
    """
    wip = load_wip_features(Path(features_path))
    conn = connect_db(Path(db))
    try:
        tier_specs = []
        if tiers:
            requested = [t.strip() for t in tiers.split(",") if t.strip()]
            for t in requested:
                if t == "tier1_modern":
                    tier_specs.append(
                        ("spine_master_v1_lanes", "EchoTier_1_YearEnd_Top40", t)
                    )
                elif t == "tier2_modern":
                    tier_specs.append(
                        ("spine_master_tier2_modern_lanes_v1", "EchoTier_2_YearEnd_Top100_Modern", t)
                    )
                elif t == "tier3_modern":
                    tier_specs.append(
                        ("spine_master_tier3_modern_lanes_v1", "EchoTier_3_YearEnd_Top200_Modern", t)
                    )
        if not tier_specs:
            tier_specs.append((table, echo_tier, "tier1_modern"))

        ab_map: Dict[str, Dict[str, Any]] = {}
        max_fallback = acousticbrainz_max_fallback or None
        if use_acousticbrainz_fallback:
            ab_map = load_acousticbrainz_feature_map(conn)

        rows: List[Dict[str, Any]] = []
        for tbl, tier_name, label in tier_specs:
            for r in load_spine_rows(
                conn,
                table=tbl,
                echo_tier=tier_name,
                year_min=year_min,
                year_max=year_max,
                tier_label=label,
                verbose=False,
            ):
                rows.append(r)

            if (
                label == "tier3_modern"
                and use_acousticbrainz_fallback
                and ab_map
            ):
                ab_rows = load_tier3_acousticbrainz_rows(
                    conn,
                    year_min=year_min,
                    year_max=year_max,
                    echo_tier=tier_name,
                    ab_features=ab_map,
                    max_fallback=max_fallback,
                    verbose=False,
                )
                rows.extend(ab_rows)

        if not rows:
            return {
                "wip_features": wip,
                "neighbors": [],
                "neighbors_by_tier": {},
                "tier1_neighbors": [],
                "tier2_neighbors": [],
                "tier3_neighbors": [],
                "decade_counts": {},
            }

        rows = merge_rows_prefer_highest_tier(rows)
        filter_notes = {
            "total_rows": len(rows),
            "skipped_missing_axes": 0,
            "skipped_non_numeric": 0,
        }

        def _valid_axes(r: Dict[str, Any]) -> bool:
            required = ["tempo", "valence", "energy", "loudness"]
            for k in required:
                v = r.get(k)
                if v is None:
                    filter_notes["skipped_missing_axes"] += 1
                    return False
                try:
                    if not math.isfinite(float(v)):
                        filter_notes["skipped_non_numeric"] += 1
                        return False
                except Exception:
                    filter_notes["skipped_non_numeric"] += 1
                    return False
            return True

        rows = [r for r in rows if _valid_axes(r)]
        stats_rows = [r for r in rows if r.get("feature_source") == "essentia_local"]
        base_rows = stats_rows or rows
        stats = compute_feature_stats(base_rows)
        for r in rows:
            r["distance"] = compute_distance(
                wip,
                r,
                stats,
                use_tempo_conf=use_tempo_confidence,
                tempo_conf_score=wip.get("tempo_confidence_score"),
                tempo_conf_threshold=tempo_confidence_threshold,
                tempo_weight_low=tempo_weight_low,
            )

        top = select_top_neighbors(rows, top_k)

        neighbors: List[Dict[str, Any]] = [
            {
                "year": r["year"],
                "artist": r["artist"],
                "title": r["title"],
                "tempo": r["tempo"],
                "valence": r["valence"],
                "energy": r["energy"],
                "loudness": r["loudness"],
                "tempo_band": r["tempo_band"],
                "valence_band": r["valence_band"],
                "energy_band": r["energy_band"],
                "distance": r["distance"],
                "tier": r.get("tier", "tier1_modern"),
                "feature_source": r.get("feature_source", "essentia_local"),
            }
            for r in top
        ]

        decade_counts: Dict[str, int] = {}
        for r in neighbors:
            dec = bucket_decade(r["year"])
            decade_counts[dec] = decade_counts.get(dec, 0) + 1

        neighbors_by_tier: Dict[str, List[Dict[str, Any]]] = {}
        for n in neighbors:
            tier_label = n.get("tier", "tier1_modern")
            neighbors_by_tier.setdefault(tier_label, []).append(n)

        return {
            "wip_features": wip,
            "neighbors": neighbors,
            "neighbors_by_tier": neighbors_by_tier,
            "tier1_neighbors": neighbors_by_tier.get("tier1_modern", []),
            "tier2_neighbors": neighbors_by_tier.get("tier2_modern", []),
            "tier3_neighbors": neighbors_by_tier.get("tier3_modern", []),
            "decade_counts": decade_counts,
            "neighbor_filter_notes": filter_notes,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# MAIN (CLI)
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()

    features_path = Path(args.features)
    result = run_echo_probe_for_features(
        features_path=str(features_path),
        db=args.db,
        table=args.table,
        echo_tier=args.echo_tier,
        year_min=args.year_min,
        year_max=args.year_max,
        top_k=args.top_k,
        tiers=args.tiers,
        use_acousticbrainz_fallback=args.use_acousticbrainz_fallback,
        acousticbrainz_max_fallback=args.acousticbrainz_max_fallback or None,
        use_tempo_confidence=args.use_tempo_confidence,
        tempo_confidence_threshold=args.tempo_confidence_threshold,
        tempo_weight_low=args.tempo_weight_low,
    )

    neighbors = result["neighbors"]
    print_neighbors(result["wip_features"], neighbors)
    summarize_neighbors(neighbors)


if __name__ == "__main__":
    main()

__all__ = [
    "band_energy",
    "band_loudness",
    "band_tempo",
    "band_valence",
    "bucket_decade",
    "compute_distance",
    "compute_feature_stats",
    "connect_db",
    "load_acousticbrainz_feature_map",
    "load_spine_rows",
    "load_tier3_acousticbrainz_rows",
    "load_wip_features",
    "main",
    "merge_rows_prefer_highest_tier",
    "parse_args",
    "print_neighbors",
    "run_echo_probe_for_features",
    "select_top_neighbors",
    "summarize_neighbors",
    "table_exists",
    "tier_priority",
    "zscore",
]
