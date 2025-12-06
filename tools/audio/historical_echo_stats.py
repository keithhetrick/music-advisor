#!/usr/bin/env python3
"""
historical_echo_stats.py

Read the historical_echo.db SQLite database and print summary statistics
for HCI scores and audio axes. This is a read-only analysis tool to help
inspect the distribution of scores (e.g., Blinding Lights vs WIPs) and
verify that calibration / WIP rules behave as expected.

Examples:

    # Basic stats for everything in the DB
    python tools/historical_echo_stats.py \
        --db data/historical_echo/historical_echo.db

    # Stats restricted to a particular corpus slice
    python tools/historical_echo_stats.py \
        --db data/historical_echo/historical_echo.db \
        --set-name 2025Q4_benchmark_100

    # Only tracks that are flagged as part of the calibration set
    python tools/historical_echo_stats.py \
        --db data/historical_echo/historical_echo.db \
        --only-calibration

    # Focus on a specific slug or partial match
    python tools/historical_echo_stats.py \
        --db data/historical_echo/historical_echo.db \
        --filter blinding_lights
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from math import floor, ceil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


@dataclass
class TrackRow:
    slug: str
    year: Optional[str]
    artist: Optional[str]
    title: Optional[str]
    set_name: Optional[str]
    in_calibration_set: bool
    in_echo_set: bool
    hci_role: Optional[str]
    hci_v1_score_raw: Optional[float]
    hci_v1_score: Optional[float]
    hci_v1_final_score: Optional[float]
    hci_audio_v2_raw: Optional[float]


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _quantile(values: Sequence[float], p: float) -> Optional[float]:
    """
    Simple quantile function with linear interpolation.

    p is in [0, 1].
    """
    if not values:
        return None
    if p <= 0:
        return float(values[0])
    if p >= 1:
        return float(values[-1])

    n = len(values)
    pos = p * (n - 1)
    lo = floor(pos)
    hi = ceil(pos)

    if lo == hi:
        return float(values[int(pos)])

    w = pos - lo
    v_lo = float(values[lo])
    v_hi = float(values[hi])
    return (1.0 - w) * v_lo + w * v_hi


def _summary_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "p10": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None,
            "max": None,
        }

    n = len(values)
    s = sum(values)
    mean = s / n
    var = sum((v - mean) ** 2 for v in values) / n if n > 0 else 0.0
    std = var ** 0.5

    sorted_vals = sorted(values)
    return {
        "count": n,
        "mean": mean,
        "std": std,
        "min": sorted_vals[0],
        "p10": _quantile(sorted_vals, 0.10),
        "p25": _quantile(sorted_vals, 0.25),
        "p50": _quantile(sorted_vals, 0.50),
        "p75": _quantile(sorted_vals, 0.75),
        "p90": _quantile(sorted_vals, 0.90),
        "max": sorted_vals[-1],
    }


def _bool_from_int(x: Any) -> bool:
    try:
        return bool(int(x))
    except Exception:
        return False


# -------------------------------------------------------------------
# Core query logic
# -------------------------------------------------------------------


def load_tracks(
    conn: sqlite3.Connection,
    set_name: Optional[str],
    only_calibration: bool,
    filter_substring: Optional[str],
) -> List[TrackRow]:
    """
    Fetch tracks joined with hci_scores, optionally filtered by:
      - set_name
      - only_calibration (in_calibration_set = 1)
      - filter_substring in slug/artist/title
    """
    conditions: List[str] = []
    params: List[Any] = []

    if set_name:
        conditions.append("t.set_name = ?")
        params.append(set_name)

    if only_calibration:
        conditions.append("t.in_calibration_set = 1")

    if filter_substring:
        like = f"%{filter_substring}%"
        conditions.append("(t.slug LIKE ? OR t.artist LIKE ? OR t.title LIKE ?)")
        params.extend([like, like, like])

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT
            t.slug,
            t.year,
            t.artist,
            t.title,
            t.set_name,
            t.in_calibration_set,
            t.in_echo_set,
            t.hci_role,
            h.hci_v1_score_raw,
            h.hci_v1_score,
            h.hci_v1_final_score,
            h.hci_audio_v2_raw
        FROM tracks t
        JOIN hci_scores h ON t.id = h.track_id
        {where_clause}
        ORDER BY t.slug ASC;
    """

    cur = conn.cursor()
    cur.execute(sql, params)
    rows: List[TrackRow] = []

    for r in cur.fetchall():
        rows.append(
            TrackRow(
                slug=r["slug"],
                year=r["year"],
                artist=r["artist"],
                title=r["title"],
                set_name=r["set_name"],
                in_calibration_set=_bool_from_int(r["in_calibration_set"]),
                in_echo_set=_bool_from_int(r["in_echo_set"]),
                hci_role=r["hci_role"],
                hci_v1_score_raw=r["hci_v1_score_raw"],
                hci_v1_score=r["hci_v1_score"],
                hci_v1_final_score=r["hci_v1_final_score"],
                hci_audio_v2_raw=r["hci_audio_v2_raw"],
            )
        )

    return rows


# -------------------------------------------------------------------
# Reporting
# -------------------------------------------------------------------


def print_stats(label: str, stats: Dict[str, Optional[float]]) -> None:
    print(f"\n[{label}]")
    print(f"  count = {stats['count']}")
    if stats["mean"] is None:
        print("  (no data)")
        return

    print(f"  mean  = {stats['mean']:.3f}")
    print(f"  std   = {stats['std']:.3f}")
    print(f"  min   = {stats['min']:.3f}")
    print(f"  p10   = {stats['p10']:.3f}")
    print(f"  p25   = {stats['p25']:.3f}")
    print(f"  p50   = {stats['p50']:.3f}")
    print(f"  p75   = {stats['p75']:.3f}")
    print(f"  p90   = {stats['p90']:.3f}")
    print(f"  max   = {stats['max']:.3f}")


def print_leaderboard(title: str, tracks: List[TrackRow], key: str, top_n: int = 10) -> None:
    """
    Print a leaderboard for either hci_v1_final_score or hci_audio_v2_raw.
    """
    print(f"\n=== {title} (top {top_n}) ===")

    # Extract the attribute dynamically
    def _score(tr: TrackRow) -> float:
        val = getattr(tr, key)
        return float(val) if val is not None else float("-inf")

    sorted_tracks = sorted(tracks, key=_score, reverse=True)
    shown = 0
    for tr in sorted_tracks:
        val = getattr(tr, key)
        if val is None:
            continue
        shown += 1
        artist_title = ""
        if tr.artist:
            artist_title += tr.artist
        if tr.title:
            if artist_title:
                artist_title += " — "
            artist_title += tr.title
        if not artist_title:
            artist_title = tr.slug

        role = tr.hci_role or ""
        role_str = f" [{role}]" if role else ""
        print(f"{shown:2d}. {val:.3f}  {artist_title}  ({tr.slug}){role_str}")
        if shown >= top_n:
            break

    if shown == 0:
        print("  (no valid scores)")


def print_sample_rows(tracks: List[TrackRow], key: str, label: str, n: int = 5) -> None:
    """
    Print a few sample rows (bottom and top) for quick sanity checks.
    """
    def _score(tr: TrackRow) -> float:
        val = getattr(tr, key)
        return float(val) if val is not None else float("inf")

    with_scores = [tr for tr in tracks if getattr(tr, key) is not None]
    if not with_scores:
        print(f"\n[Sample {label}] no rows with {key}")
        return

    sorted_tracks = sorted(with_scores, key=_score)
    bottom = sorted_tracks[:n]
    top = list(reversed(sorted_tracks[-n:]))

    print(f"\n[Sample {label}] bottom {n} by {key}:")
    for tr in bottom:
        val = getattr(tr, key)
        artist_title = ""
        if tr.artist:
            artist_title += tr.artist
        if tr.title:
            if artist_title:
                artist_title += " — "
            artist_title += tr.title
        if not artist_title:
            artist_title = tr.slug
        print(f"  {val:.3f}  {artist_title} ({tr.slug})")

    print(f"\n[Sample {label}] top {n} by {key}:")
    for tr in top:
        val = getattr(tr, key)
        artist_title = ""
        if tr.artist:
            artist_title += tr.artist
        if tr.title:
            if artist_title:
                artist_title += " — "
            artist_title += tr.title
        if not artist_title:
            artist_title = tr.slug
        print(f"  {val:.3f}  {artist_title} ({tr.slug})")


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Summarize HCI distributions from historical_echo.db."
    )
    ap.add_argument(
        "--db",
        required=True,
        help="Path to historical_echo.db (SQLite).",
    )
    ap.add_argument(
        "--set-name",
        help="Optional set_name filter (e.g. 2025Q4_benchmark_100).",
    )
    ap.add_argument(
        "--only-calibration",
        action="store_true",
        help="Restrict to tracks where in_calibration_set = 1.",
    )
    ap.add_argument(
        "--filter",
        help="Substring to match in slug/artist/title (e.g. 'blinding_lights').",
    )

    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"[ERROR] DB not found: {db_path}")

    conn = _connect(db_path)

    tracks = load_tracks(
        conn,
        set_name=args.set_name,
        only_calibration=args.only_calibration,
        filter_substring=args.filter,
    )

    if not tracks:
        print("[INFO] No matching tracks in DB for given filters.")
        return

    print(f"[INFO] Loaded {len(tracks)} tracks from {db_path}")
    if args.set_name:
        print(f"[INFO]   set_name filter: {args.set_name}")
    if args.only_calibration:
        print(f"[INFO]   only calibration set: True")
    if args.filter:
        print(f"[INFO]   text filter: {args.filter!r}")

    # --- Aggregate stats ---
    v1_final_vals = [t.hci_v1_final_score for t in tracks if t.hci_v1_final_score is not None]
    v1_cal_vals = [t.hci_v1_score for t in tracks if t.hci_v1_score is not None]
    v2_raw_vals = [t.hci_audio_v2_raw for t in tracks if t.hci_audio_v2_raw is not None]

    print_stats("HCI_v1_final_score", _summary_stats(v1_final_vals))
    print_stats("HCI_v1_score (calibrated)", _summary_stats(v1_cal_vals))
    print_stats("HCI_audio_v2.raw", _summary_stats(v2_raw_vals))

    # --- Leaderboards ---
    print_leaderboard("HCI_v1_final_score", tracks, key="hci_v1_final_score", top_n=10)
    print_leaderboard("HCI_audio_v2.raw", tracks, key="hci_audio_v2_raw", top_n=10)

    # --- Sample extremes for sanity ---
    print_sample_rows(tracks, key="hci_v1_final_score", label="HCI_v1_final_score", n=5)

    conn.close()


if __name__ == "__main__":
    main()
