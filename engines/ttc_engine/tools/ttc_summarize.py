#!/usr/bin/env python3
"""
Summarize TTC sidecar tables for quick inspection/narrative prep.

Outputs overall stats for ttc_corpus_stats (and ttc_local_estimates if present),
plus optional decade breakdowns when year metadata exists.
"""
from __future__ import annotations

import argparse
import math
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ma_config.paths import get_historical_echo_db_path

DEFAULT_DB = get_historical_echo_db_path()


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def percentile(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    if q <= 0:
        return values[0]
    if q >= 1:
        return values[-1]
    idx = (len(values) - 1) * q
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return values[int(idx)]
    frac = idx - lo
    return values[lo] + (values[hi] - values[lo]) * frac


def summarize(values: Iterable[Optional[float]]) -> Dict[str, Optional[float]]:
    vals = list(values)
    cleaned = sorted([v for v in vals if v is not None])
    if not cleaned:
        return {k: None for k in ("count", "missing", "min", "max", "mean", "median", "p25", "p75")}
    total = len(vals)
    count = len(cleaned)
    missing = total - count
    mean = sum(cleaned) / count if count else None
    mid = percentile(cleaned, 0.5)
    p25 = percentile(cleaned, 0.25)
    p75 = percentile(cleaned, 0.75)
    return {
        "count": count,
        "missing": missing,
        "min": cleaned[0],
        "max": cleaned[-1],
        "mean": mean,
        "median": mid,
        "p25": p25,
        "p75": p75,
    }


def fmt(val: Optional[float]) -> str:
    if val is None:
        return "None"
    return f"{val:.2f}"


def fetch_corpus(conn: sqlite3.Connection, dataset: Optional[str]) -> List[Dict[str, object]]:
    if not table_exists(conn, "ttc_corpus_stats"):
        return []
    cur = conn.cursor()
    if dataset:
        cur.execute(
            """
            SELECT ttc_seconds, year FROM ttc_corpus_stats
            WHERE ttc_seconds IS NOT NULL AND dataset_name=?
            """,
            (dataset,),
        )
    else:
        cur.execute("SELECT ttc_seconds, year FROM ttc_corpus_stats WHERE ttc_seconds IS NOT NULL")
    rows = [{"ttc_seconds": r[0], "year": r[1]} for r in cur.fetchall()]
    return rows


def fetch_local(conn: sqlite3.Connection) -> List[float]:
    if not table_exists(conn, "ttc_local_estimates"):
        return []
    cur = conn.cursor()
    cur.execute("SELECT ttc_seconds FROM ttc_local_estimates WHERE ttc_seconds IS NOT NULL")
    return [r[0] for r in cur.fetchall()]


def decade(year: Optional[int]) -> Optional[int]:
    if year is None:
        return None
    try:
        return int(year) // 10 * 10
    except Exception:
        return None


def summarize_decades(rows: List[Dict[str, object]]) -> List[Tuple[str, Dict[str, Optional[float]]]]:
    buckets: Dict[int, List[float]] = {}
    for row in rows:
        dec = decade(row.get("year"))
        val = row.get("ttc_seconds")
        if dec is None or val is None:
            continue
        buckets.setdefault(dec, []).append(float(val))
    out: List[Tuple[str, Dict[str, Optional[float]]]] = []
    for dec, vals in sorted(buckets.items()):
        out.append((f"{dec}s", summarize(vals)))
    return out


def print_summary(label: str, stats: Dict[str, Optional[float]]) -> None:
    print(f"{label}:")
    print(
        "  count={count} missing={missing} mean={mean} median={median} p25={p25} p75={p75} min={min} max={max}".format(
            count=stats.get("count"),
            missing=stats.get("missing"),
            mean=fmt(stats.get("mean")),
            median=fmt(stats.get("median")),
            p25=fmt(stats.get("p25")),
            p75=fmt(stats.get("p75")),
            min=fmt(stats.get("min")),
            max=fmt(stats.get("max")),
        )
    )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Summarize TTC sidecar tables (corpus/local).")
    ap.add_argument("--db", default=str(DEFAULT_DB), help=f"Path to SQLite DB (default: {DEFAULT_DB}).")
    ap.add_argument("--dataset", help="Optional dataset_name filter for corpus stats (e.g., mcgill_billboard).")
    ap.add_argument("--no-decades", action="store_true", help="Skip decade breakdown.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")
    conn = sqlite3.connect(db_path)

    corpus_rows = fetch_corpus(conn, args.dataset)
    if corpus_rows:
        stats = summarize([r["ttc_seconds"] for r in corpus_rows])
        label = "ttc_corpus_stats"
        if args.dataset:
            label += f" (dataset={args.dataset})"
        print_summary(label, stats)
        if not args.no_decades:
            decade_stats = summarize_decades(corpus_rows)
            if decade_stats:
                print("Decade breakdown:")
                for dec, st in decade_stats:
                    print(f"  {dec}: median={fmt(st.get('median'))} p25={fmt(st.get('p25'))} p75={fmt(st.get('p75'))} count={st.get('count')}")
            else:
                print("Decade breakdown: no year metadata available.")
    else:
        print("ttc_corpus_stats: no table or no rows with ttc_seconds.")

    local_vals = fetch_local(conn)
    if local_vals:
        print_summary("ttc_local_estimates", summarize(local_vals))
    else:
        print("ttc_local_estimates: no table or no rows with ttc_seconds.")
    conn.close()


if __name__ == "__main__":
    main()
