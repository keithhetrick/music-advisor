#!/usr/bin/env python3
"""
Tempo norms / BPM lane sidecar generator.

- Input: lane hit tempos (Tier lanes from lyric_intel.db) + song tempo.
- Output: structured JSON sidecar plus advisory labels for downstream overlays.

Data sources (aligned with existing assets):
- Song BPM lives in `features_song.tempo_bpm` inside lyric_intel.db (populated via ingest/feature writers).
- Lane membership comes from `songs.tier` + `songs.era_bucket` (see ma_lyrics_engine.lanes.lane_key).
- Tier 1/Top 40 hit BPMs are stored in the same DB; we read them via tier/era filters.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env, make_logger  # type: ignore[import-not-found]  # noqa: E402
from ma_audio_engine.adapters.logging_adapter import log_stage_end, log_stage_start  # type: ignore[import-not-found]  # noqa: E402
from ma_config.paths import get_lyric_intel_db_path  # type: ignore[import-not-found]  # noqa: E402
from ma_lyrics_engine.schema import ensure_schema  # type: ignore[import-not-found]  # noqa: E402
from tools import names  # noqa: E402
from tools.tempo_relationships import (  # noqa: E402
    adaptive_bin_width,
    bin_counts,
    bin_center,
    find_peak_clusters,
    fold_series_to_range,
    lane_shape_metrics,
    neighbor_bins_for,
    neighbor_bins_with_decay,
    percentile_band,
    percentile_band_weighted,
    smooth_counts,
    smooth_counts_gaussian,
    trim_outliers,
    valid_bpm,
    validate_tempo_series,
)
try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None

TEMPO_ANALYSIS_VERSION = "v1.0"


@dataclass
class TempoLaneStats:
    lane_id: str
    bin_width: float
    median_bpm: float
    iqr_low: float
    iqr_high: float
    peak_cluster_min: float
    peak_cluster_max: float
    total_hits: int


@dataclass
class TempoSongPlacement:
    song_bpm: float
    song_bin_center: float
    song_bin_count: int
    song_bin_percent: float
    neighbor_bins: List[Dict[str, float]]


@dataclass
class TempoAdvisory:
    advisory_label: str
    suggested_bpm_range: List[float]
    suggested_delta_bpm: List[float]
    advisory_text: str


def _parse_lane_id(lane_id: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Extract (tier, era_bucket) from lane_id strings.
    Supported forms:
    - tier1__2015_2024 (explicit era)
    - tier1_modern / tier1 (tier only; uses all eras)
    """
    tier: Optional[int] = None
    era_bucket: Optional[str] = None
    lane_clean = lane_id.strip()
    m = re.match(r"tier(?P<tier>\d+)(?:[_]{1,2}(?P<label>[A-Za-z0-9_]+))?", lane_clean)
    if m:
        tier = int(m.group("tier"))
        label = m.group("label")
        if label:
            if re.match(r"^\d{4}_\d{4}$", label):
                era_bucket = label
            elif label.lower() == "modern":
                era_bucket = None
    return tier, era_bucket


def _apply_env_overrides(args: argparse.Namespace, defaults: Dict[str, Any]) -> argparse.Namespace:
    """
    Allow env JSON to override defaults when CLI flags are not provided.
    Env: TEMPO_NORMS_OPTS='{"bin_width":1.0,"neighbor_steps":2,...}'
    CLI takes precedence over env; env only applies when the arg is still at its default.
    """
    raw = os.getenv("TEMPO_NORMS_OPTS")
    if not raw:
        return args
    try:
        data = json.loads(raw)
    except Exception:
        return args
    for key, val in data.items():
        if key in defaults and getattr(args, key, None) == defaults[key]:
            setattr(args, key, val)
    return args


def compute_lane_stats(
    lane_id: str,
    bpms: List[float],
    bin_width: float,
    smoothing: float = 0.0,
    smoothing_method: str = "simple",
) -> Tuple[TempoLaneStats, Dict[float, float], List[Dict[str, float]], Dict[str, float]]:
    if not bpms:
        raise ValueError(f"Lane {lane_id} has no BPM values to analyze.")
    raw_counts = bin_counts(bpms, bin_width)
    if smoothing_method == "gaussian":
        counts = smooth_counts_gaussian(raw_counts, sigma_bins=max(smoothing, 1e-9))
    else:
        counts = smooth_counts(raw_counts, smoothing=smoothing)
    ordered = sorted(bpms)
    median = statistics.median(ordered)
    try:
        quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
        q1, q3 = quartiles[0], quartiles[2]
    except Exception:
        # Fallback for very small samples
        q1 = ordered[0]
        q3 = ordered[-1]

    # Peak cluster: contiguous bins sharing the max count.
    if counts:
        max_count = max(counts.values())
        max_bins = [c for c, ct in counts.items() if ct == max_count]
        clusters: List[List[float]] = []
        for c in sorted(max_bins):
            if not clusters or abs(c - clusters[-1][-1]) > bin_width + 1e-9:
                clusters.append([c])
            else:
                clusters[-1].append(c)
        # Choose cluster with most total hits (len * max_count), tie-break by proximity to lane median.
        def cluster_score(cluster: List[float]) -> tuple:
            total_hits_cluster = len(cluster) * max_count
            center = (cluster[0] + cluster[-1]) / 2.0
            return (total_hits_cluster, -abs(center - statistics.median(ordered)))

        peak_bins = max(clusters, key=cluster_score)
        peak_min = peak_bins[0] - (bin_width / 2.0)
        peak_max = peak_bins[-1] + (bin_width / 2.0)
    else:
        peak_min = median - bin_width
        peak_max = median + bin_width

    stats = TempoLaneStats(
        lane_id=lane_id,
        bin_width=bin_width,
        median_bpm=median,
        iqr_low=q1,
        iqr_high=q3,
        peak_cluster_min=peak_min,
        peak_cluster_max=peak_max,
        total_hits=len(bpms),
    )
    clusters = find_peak_clusters(counts, bin_width)
    primary_range = clusters[0] if clusters else None
    if primary_range:
        stats.peak_cluster_min = primary_range["min_bpm"]
        stats.peak_cluster_max = primary_range["max_bpm"]
    shape = lane_shape_metrics(counts)
    return stats, counts, clusters, shape


def compute_song_placement(
    bpms: List[float],
    song_bpm: float,
    bin_width: float,
    counts: Optional[Dict[float, float]] = None,
    neighbor_steps: int = 2,
    neighbor_decay: float = 0.5,
) -> TempoSongPlacement:
    counts = counts or bin_counts(bpms, bin_width)
    song_center = bin_center(song_bpm, bin_width)
    song_count = counts.get(song_center, 0)
    total = sum(counts.values()) or 1
    song_percent = song_count / total
    neighbor_bins = neighbor_bins_with_decay(counts, song_center, steps=neighbor_steps, decay=neighbor_decay)
    if not neighbor_bins:  # fallback to immediate neighbors if decay mode produced none
        neighbor_bins = neighbor_bins_for(counts, song_center)
    return TempoSongPlacement(
        song_bpm=song_bpm,
        song_bin_center=song_center,
        song_bin_count=song_count,
        song_bin_percent=song_percent,
        neighbor_bins=neighbor_bins,
    )


def build_advisory(stats: TempoLaneStats, placement: TempoSongPlacement, counts: Dict[float, float]) -> TempoAdvisory:
    total_hits = max(1, stats.total_hits)
    peak_count = max(counts.values()) if counts else 0
    peak_percent = peak_count / total_hits
    density_ratio = (placement.song_bin_count / peak_count) if peak_count else 0.0
    in_iqr = stats.iqr_low <= placement.song_bpm <= stats.iqr_high
    in_peak = stats.peak_cluster_min <= placement.song_bpm <= stats.peak_cluster_max
    near_peak = in_peak or abs(placement.song_bpm - stats.median_bpm) <= max(4.0, stats.bin_width * 2)

    label = "low_density_pocket"
    suggested_range: List[float] = []
    if in_iqr and (density_ratio >= 0.4 or placement.song_bin_percent >= max(0.01, peak_percent * 0.3)):
        label = "main_cluster"
    elif near_peak or in_iqr:
        label = "edge_cluster"
    if not in_peak and peak_count > 0:
        suggested_range = [stats.peak_cluster_min, stats.peak_cluster_max]

    suggested_delta: List[float] = []
    if suggested_range:
        suggested_delta = [round(suggested_range[0] - placement.song_bpm, 2), round(suggested_range[1] - placement.song_bpm, 2)]

    def _percent_fmt(p: float) -> str:
        return f"{p*100:.1f}%"

    def _nudge_sentence(delta: List[float]) -> str:
        if not delta:
            return ""
        d_min, d_max = delta
        # Normalize ordering for readability
        d_lo, d_hi = sorted([d_min, d_max])
        band = f"{stats.peak_cluster_min:.1f}–{stats.peak_cluster_max:.1f} BPM"
        if d_hi < 0:
            return f"To sit in that medium, slow down by ~{abs(d_hi):.1f}–{abs(d_lo):.1f} BPM toward {band}."
        if d_lo > 0:
            return f"To sit in that medium, speed up by ~{d_lo:.1f}–{d_hi:.1f} BPM toward {band}."
        return f"To sit in that medium, nudge toward {band} (roughly -{abs(d_lo):.1f} to +{d_hi:.1f} BPM from current)."

    lane_density = _percent_fmt(placement.song_bin_percent)
    peak_density = _percent_fmt(peak_percent)
    nudge_line = _nudge_sentence(suggested_delta)
    hit_medium = f"historical hit medium around {stats.peak_cluster_min:.1f}–{stats.peak_cluster_max:.1f} BPM"
    if label == "main_cluster":
        text = (
            f"You’re in the main tempo band for lane {stats.lane_id} (IQR {stats.iqr_low:.1f}–{stats.iqr_high:.1f} BPM). "
            f"The {hit_medium} holds ~{peak_density} of hits; your bin is similarly dense. No tempo change needed unless it’s an intentional creative choice. {nudge_line}"
        )
    elif label == "edge_cluster":
        text = (
            f"You’re close to the {hit_medium} (~{peak_density} of hits). "
            f"Consider a small tempo nudge if you want to sit directly in that medium-density pocket; staying here keeps a slightly off-center feel. {nudge_line}"
        )
    else:
        text = (
            f"Your tempo sits in a sparse pocket for lane {stats.lane_id} (~{lane_density} of hits at this bin) while the {hit_medium} carries ~{peak_density} of the lane. "
            f"If the off-center feel is intentional, keep it; otherwise, nudging toward that band will feel more lane-typical and historically hit-aligned. {nudge_line}"
        )

    return TempoAdvisory(
        advisory_label=label,
        suggested_bpm_range=suggested_range,
        suggested_delta_bpm=suggested_delta,
        advisory_text=text,
    )


def build_sidecar_payload(
    lane_id: str,
    song_bpm: float,
    bin_width: float,
    bpms: List[float],
    smoothing: float = 0.0,
    smoothing_sigma: float = 1.0,
    bpm_precision: int = 2,
    smoothing_method: str = "simple",
    neighbor_steps: int = 2,
    neighbor_decay: float = 0.5,
    weights: Optional[List[float]] = None,
    fold_low: Optional[float] = None,
    fold_high: Optional[float] = None,
    trim_lower_pct: float = 0.0,
    trim_upper_pct: float = 0.0,
) -> Dict[str, Any]:
    lane_bpms = bpms
    lane_weights = weights
    if trim_lower_pct > 0 or trim_upper_pct > 0:
        lane_bpms, lane_weights, _ = trim_outliers(lane_bpms, lane_weights, lower_pct=trim_lower_pct, upper_pct=trim_upper_pct)
    if fold_low and fold_high:
        lane_bpms = fold_series_to_range(lane_bpms, low=fold_low, high=fold_high)
        song_bpm_for_bins = fold_series_to_range([song_bpm], low=fold_low, high=fold_high)[0] if valid_bpm(song_bpm) else song_bpm
    else:
        song_bpm_for_bins = song_bpm
    smoothing_value = smoothing_sigma if smoothing_method == "gaussian" else smoothing
    stats, counts, clusters, shape = compute_lane_stats(
        lane_id,
        lane_bpms,
        bin_width,
        smoothing=smoothing_value,
        smoothing_method=smoothing_method,
    )
    placement = compute_song_placement(
        lane_bpms,
        song_bpm_for_bins,
        bin_width,
        counts=counts,
        neighbor_steps=neighbor_steps,
        neighbor_decay=neighbor_decay,
    )
    advisory = build_advisory(stats, placement, counts)
    peak_percent = 0.0
    if counts and stats.total_hits > 0:
        peak_percent = max(counts.values()) / stats.total_hits
    hit_medium_band = percentile_band_weighted(lane_bpms, lane_weights, lower=0.2, upper=0.8)

    def _round_val(val: Optional[float], digits: int = 2) -> Optional[float]:
        if val is None:
            return None
        return round(val, digits)

    payload = {
        "tempo_analysis_version": TEMPO_ANALYSIS_VERSION,
        "lane_id": lane_id,
        "song_bpm": _round_val(song_bpm, digits=bpm_precision),
        "bin_width": bin_width,
        "lane_stats": {
            "median_bpm": _round_val(stats.median_bpm, digits=bpm_precision),
            "iqr_bpm": [_round_val(stats.iqr_low, digits=bpm_precision), _round_val(stats.iqr_high, digits=bpm_precision)],
            "peak_cluster_bpm_range": [_round_val(stats.peak_cluster_min, digits=bpm_precision), _round_val(stats.peak_cluster_max, digits=bpm_precision)],
            "total_hits": stats.total_hits,
            "peak_cluster_percent_of_lane": round(peak_percent, 4) if peak_percent else 0.0,
            "hit_medium_percentile_band": [_round_val(hit_medium_band[0], digits=bpm_precision), _round_val(hit_medium_band[1], digits=bpm_precision)],
            "peak_clusters": clusters,
            "shape": shape,
        },
        "song_bin": {
            "center_bpm": _round_val(placement.song_bin_center, digits=bpm_precision),
            "hit_count": int(round(placement.song_bin_count)),
            "percent_of_lane": round(placement.song_bin_percent, 4),
        },
        "neighbor_bins": [
            {
                "center_bpm": _round_val(nb["center_bpm"], digits=bpm_precision),
                "hit_count": int(nb["hit_count"]),
                "percent_of_lane": round(float(nb["percent_of_lane"]), 4),
                "weight": round(float(nb.get("weight", nb["percent_of_lane"])), 4),
                "step": int(nb.get("step", 1)),
            }
            for nb in placement.neighbor_bins
        ],
        "suggested_bpm_range": [_round_val(v) for v in advisory.suggested_bpm_range] if advisory.suggested_bpm_range else [],
        "suggested_delta_bpm": advisory.suggested_delta_bpm,
        "advisory_label": advisory.advisory_label,
        "advisory_text": advisory.advisory_text,
    }
    return payload


def load_lane_bpms(conn: sqlite3.Connection, lane_id: str) -> List[float]:
    """
    Fetch BPMs for a lane. Prefer a dedicated lane_bpms table if present; otherwise
    fall back to features_song + songs filters (tier/era_bucket).
    """
    # Fallback: explicit lane_bpms table
    try:
        cur = conn.execute("SELECT bpm FROM lane_bpms WHERE lane_id = ? AND bpm IS NOT NULL AND bpm > 0", (lane_id,))
        lane_rows = [float(row[0]) for row in cur.fetchall() if valid_bpm(row[0])]
        if lane_rows:
            return lane_rows
        else:
            # If lane_bpms exists but is empty for this lane, do not force a legacy fallback;
            # returning [] will cause the caller to skip gracefully.
            return []
    except sqlite3.Error:
        pass  # table may not exist; continue to legacy path

    # Legacy path: only attempt if the needed columns exist
    try:
        cur = conn.execute("PRAGMA table_info(songs)")
        song_cols = {row[1] for row in cur.fetchall()}
        if not {"tier", "era_bucket"}.issubset(song_cols):
            return []
    except sqlite3.Error:
        return []

    tier, era_bucket = _parse_lane_id(lane_id)
    query = """
        SELECT f.tempo_bpm
        FROM features_song f
        JOIN songs s ON s.song_id = f.song_id
        WHERE f.tempo_bpm IS NOT NULL AND f.tempo_bpm > 0
    """
    params: List[Any] = []
    if tier is not None:
        query += " AND s.tier = ?"
        params.append(tier)
    if era_bucket:
        query += " AND s.era_bucket = ?"
        params.append(era_bucket)
    cur = conn.execute(query, tuple(params))
    bpms = [float(row[0]) for row in cur.fetchall() if valid_bpm(row[0])]
    return bpms


def load_song_bpm(conn: sqlite3.Connection, song_id: str) -> Optional[float]:
    cur = conn.execute("SELECT tempo_bpm FROM features_song WHERE song_id=?", (song_id,))
    row = cur.fetchone()
    if not row:
        return None
    try:
        bpm_val = float(row[0]) if row[0] is not None else None
    except Exception:
        return None
    return bpm_val if valid_bpm(bpm_val) else None


def _validate_payload(payload: dict) -> list[str]:
    """Best-effort schema validation if jsonschema is available."""
    warnings: list[str] = []
    if jsonschema is None:
        return warnings
    schema_path = Path(__file__).resolve().parent / "tempo_norms_schema.json"
    try:
        import json
        schema = json.loads(schema_path.read_text())
        jsonschema.validate(payload, schema)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"schema_validation_error:{exc}")
    return warnings


def derive_out_path(song_id: str, out: Optional[str], out_dir: Optional[str]) -> Path:
    if out:
        return Path(out).expanduser().resolve()
    suffix = names.tempo_norms_sidecar_suffix()
    base = Path(out_dir).expanduser().resolve() if out_dir else Path.cwd()
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{song_id}{suffix}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute tempo lane norms + advisory sidecar.")
    ap.add_argument("--song-id", required=True, help="Song identifier used in lyric_intel.db (slug).")
    ap.add_argument("--lane-id", required=True, help="Lane identifier (e.g., tier1_modern or tier1__2015_2024).")
    ap.add_argument("--song-bpm", type=float, default=None, help="Optional song BPM override (falls back to DB lookup).")
    ap.add_argument("--bin-width", type=float, default=2.0, help="BPM bin width for histogram (default: 2 BPM).")
    ap.add_argument("--db", default=str(get_lyric_intel_db_path()), help="Path to lyric_intel.db (features + lanes).")
    ap.add_argument("--out", help="Exact output path for tempo norms sidecar JSON.")
    ap.add_argument("--out-dir", help="Output directory (defaults to current working directory).")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing sidecar if present.")
    ap.add_argument("--smoothing", type=float, default=0.0, help="Neighbor smoothing factor for histogram bins (0–1).")
    ap.add_argument("--bpm-precision", type=int, default=2, help="Decimal precision when emitting BPM values.")
    ap.add_argument("--smoothing-method", choices=["simple", "gaussian"], default="simple", help="Smoothing kernel to use.")
    ap.add_argument("--smoothing-sigma", type=float, default=1.0, help="Sigma (in bins) for gaussian smoothing.")
    ap.add_argument("--neighbor-steps", type=int, default=2, help="Neighbor depth for adjacency guidance.")
    ap.add_argument("--neighbor-decay", type=float, default=0.5, help="Decay factor for neighbor weights (per step).")
    ap.add_argument("--adaptive-bin-width", action="store_true", help="Use adaptive bin width (Freedman–Diaconis) instead of fixed.")
    ap.add_argument("--adaptive-min", type=float, default=1.0, help="Minimum bin width when adaptive is on.")
    ap.add_argument("--adaptive-max", type=float, default=6.0, help="Maximum bin width when adaptive is on.")
    ap.add_argument("--trim-lower-pct", type=float, default=0.0, help="Lower percentile trim (0–1).")
    ap.add_argument("--trim-upper-pct", type=float, default=0.0, help="Upper percentile trim (0–1).")
    ap.add_argument("--fold-low", type=float, help="Optional lower bound for folding tempos (halftime/doubletime normalization).")
    ap.add_argument("--fold-high", type=float, help="Optional upper bound for folding tempos (halftime/doubletime normalization).")
    ap.add_argument("--timeout-seconds", type=float, default=None, help="Optional timeout for DB/processing (env TEMPO_NORMS_TIMEOUT).")
    add_log_sandbox_arg(ap)
    defaults = {action.dest: action.default for action in ap._actions if action.dest != "help"}
    args = ap.parse_args()
    args = _apply_env_overrides(args, defaults)

    apply_log_sandbox_env(args)
    log = make_logger("tempo_norms_sidecar")
    # Optional timeout env override
    if args.timeout_seconds is None:
        env_timeout = os.getenv("TEMPO_NORMS_TIMEOUT")
        if env_timeout:
            try:
                args.timeout_seconds = float(env_timeout)
            except Exception:
                args.timeout_seconds = None

    out_path = derive_out_path(args.song_id, args.out, args.out_dir)
    if out_path.exists() and not args.overwrite:
        log(f"[SKIP] tempo norms sidecar already exists: {out_path}")
        return 0

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        log(f"[WARN] tempo_norms_sidecar skipping: DB not found ({db_path})")
        log_stage_end(log, "tempo_norms_sidecar", status="skip_missing_db", out=str(out_path))
        return 0
    if args.bin_width <= 0 and not args.adaptive_bin_width:
        raise SystemExit("--bin-width must be > 0")
    if args.smoothing < 0:
        raise SystemExit("--smoothing must be >= 0")
    if args.neighbor_steps < 1:
        raise SystemExit("--neighbor-steps must be >= 1")
    if args.trim_lower_pct < 0 or args.trim_upper_pct < 0 or args.trim_lower_pct >= 1 or args.trim_upper_pct >= 1:
        raise SystemExit("trim percentiles must be within [0,1)")
    if (args.fold_low is None) != (args.fold_high is None):
        raise SystemExit("Both --fold-low and --fold-high must be set together.")
    if args.fold_low is not None and args.fold_high is not None and args.fold_low >= args.fold_high:
        raise SystemExit("--fold-low must be < --fold-high.")
    if args.smoothing_method == "gaussian" and args.smoothing_sigma <= 0:
        raise SystemExit("--smoothing-sigma must be > 0 when gaussian smoothing is used.")

    log_stage_start(log, "tempo_norms_sidecar", song_id=args.song_id, lane_id=args.lane_id, db=str(db_path), out=str(out_path))
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)

        song_bpm = args.song_bpm
        if song_bpm is None:
            song_bpm = load_song_bpm(conn, args.song_id)
        if song_bpm is None:
            log(f"[WARN] tempo_norms_sidecar skipping: no song BPM for {args.song_id}")
            log_stage_end(log, "tempo_norms_sidecar", status="skip_missing_bpm", out=str(out_path))
            return 0
        if not valid_bpm(song_bpm):
            raise SystemExit(f"Song BPM invalid/out of range: {song_bpm}")

        lane_bpms = load_lane_bpms(conn, args.lane_id)
        if not lane_bpms:
            log(f"[WARN] tempo_norms_sidecar skipping: no lane BPM data for lane_id={args.lane_id}")
            log_stage_end(log, "tempo_norms_sidecar", status="skip_no_lane_data", out=str(out_path))
            return 0
        lane_bpms, lane_weights, validation_warnings = validate_tempo_series(lane_bpms, min_count=1)
    finally:
        conn.close()

    if validation_warnings:
        log(f"[WARN] tempo_norms validation warnings: {validation_warnings}")
    bin_width = args.bin_width
    if args.adaptive_bin_width:
        bin_width = adaptive_bin_width(lane_bpms, min_width=args.adaptive_min, max_width=args.adaptive_max)
    payload = build_sidecar_payload(
        args.lane_id,
        song_bpm,
        bin_width,
        lane_bpms,
        smoothing=args.smoothing,
        smoothing_sigma=args.smoothing_sigma,
        bpm_precision=args.bpm_precision,
        smoothing_method=args.smoothing_method if args.smoothing_method != "gaussian" else ("gaussian" if args.smoothing_sigma > 0 else "simple"),
        neighbor_steps=args.neighbor_steps,
        neighbor_decay=args.neighbor_decay,
        weights=lane_weights,
        fold_low=args.fold_low,
        fold_high=args.fold_high,
        trim_lower_pct=args.trim_lower_pct,
        trim_upper_pct=args.trim_upper_pct,
    )
    validation_warnings = _validate_payload(payload)
    if validation_warnings:
        log(f"[WARN] tempo norms schema warnings: {validation_warnings}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log(f"[OK] Wrote tempo norms sidecar: {out_path}")

    log_stage_end(log, "tempo_norms_sidecar", status="ok", out=str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
