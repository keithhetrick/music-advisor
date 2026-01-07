#!/usr/bin/env python
"""
hci_v2_build_targets.py

Compute EchoTarget_v2 labels for the core 1,600-song historical echo spine.

- Reads from SQLite: core_spine table in historical_echo.db
- For each track, computes:
    s_rank, s_weeks, s_peak ∈ [0,1]
    success_index_raw
    echo_z
    EchoTarget_v2 ∈ (0,1) via logistic on z
    echo_decile (1–10)
- Writes:
    1) CSV snapshot (for audit / modeling)
    2) hci_v2_targets table in the same DB

Usage example:

  cd ~/music-advisor

  python tools/hci_v2_build_targets.py \
    --db data/private/local_assets/historical_echo/historical_echo.db \
    --out-csv data/private/local_assets/hci_v2/hci_v2_targets_pop_us_1985_2024.csv \
    --reset-targets

"""

import argparse
import csv
import math
import sqlite3
import statistics
from typing import Any, Dict, List, Optional, Tuple
from shared.security import db as sec_db
from shared.config.paths import get_hci_v2_targets_csv, get_historical_echo_db_path


def _log(msg: str) -> None:
    print(f"[INFO] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _err(msg: str) -> None:
    print(f"[ERROR] {msg}")


def fetch_core_spine_rows(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    # Validate table name against existing tables to avoid unsafe interpolation.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing = {row[0] for row in cur.fetchall()}
    sec_db.validate_table_name(table, allowed=existing)
    _log(f"Loading rows from table '{table}'")
    cur = sec_db.safe_execute(conn, f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    rows = []
    for raw in cur.fetchall():
        rows.append({col: val for col, val in zip(cols, raw)})
    _log(f"Loaded {len(rows)} rows from {table}")
    return rows


def _safe_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def compute_components(
    rows: List[Dict[str, Any]],
    top_n_per_year: int = 40,
    weeks_cap: Optional[int] = None,
    weeks_cap_percentile: float = 0.95,
    w_rank: float = 0.5,
    w_weeks: float = 0.3,
    w_peak: float = 0.2,
) -> List[Dict[str, Any]]:
    """
    Add s_rank, s_weeks, s_peak, success_index_raw to each row.

    - weeks_cap:
        If not None and > 0, use this fixed cap.
        Else, compute cap as the given percentile of weeks_on_chart values.
    - weights are normalized internally so they sum to 1.0.
    """
    # Extract weeks_on_chart to determine cap if needed
    weeks_values: List[int] = []
    for r in rows:
        w = _safe_int(r.get("weeks_on_chart") or r.get("wks_on_chart"))
        if w is not None and w > 0:
            weeks_values.append(w)

    if weeks_cap is None or weeks_cap <= 0:
        if weeks_values:
            weeks_values_sorted = sorted(weeks_values)
            n = len(weeks_values_sorted)
            p = min(max(weeks_cap_percentile, 0.0), 1.0)
            idx = int(round((n - 1) * p))
            weeks_cap = weeks_values_sorted[idx]
            _log(f"Computed weeks_cap from percentile {p:.2f}: {weeks_cap}")
        else:
            weeks_cap = 40
            _warn("No weeks_on_chart values; defaulting weeks_cap=40")
    else:
        _log(f"Using fixed weeks_cap={weeks_cap}")

    # Normalize weights
    w_sum = w_rank + w_weeks + w_peak
    if w_sum <= 0:
        _err("Weights sum to zero or negative; falling back to equal weights.")
        w_rank = w_weeks = w_peak = 1.0
        w_sum = 3.0
    w_rank_n = w_rank / w_sum
    w_weeks_n = w_weeks / w_sum
    w_peak_n = w_peak / w_sum
    _log(
        f"Using normalized weights: w_rank={w_rank_n:.3f}, "
        f"w_weeks={w_weeks_n:.3f}, w_peak={w_peak_n:.3f}"
    )

    augmented: List[Dict[str, Any]] = []

    for r in rows:
        year = _safe_int(r.get("year"))
        year_end_rank = _safe_int(r.get("year_end_rank") or r.get("year_end_pos") or r.get("rank"))
        title = r.get("title")
        artist = r.get("artist")

        if year is None or year_end_rank is None:
            _warn(f"Skipping row with missing year/year_end_rank: {title} — {artist}")
            continue

        # 1) s_rank ∈ [0,1], top_n_per_year assumed
        # clamp rank to [1, top_n_per_year]
        if year_end_rank < 1:
            year_end_rank = 1
        if year_end_rank > top_n_per_year:
            year_end_rank = top_n_per_year
        s_rank = 1.0 - (year_end_rank - 1) / float(max(top_n_per_year - 1, 1))

        # 2) s_weeks ∈ [0,1]
        weeks = _safe_int(r.get("weeks_on_chart") or r.get("wks_on_chart")) or 0
        if weeks < 0:
            weeks = 0
        s_weeks = min(weeks, weeks_cap) / float(max(weeks_cap, 1))

        # 3) s_peak ∈ [0,1]
        best_rank = _safe_int(r.get("best_rank") or r.get("peak_pos"))
        if best_rank is None:
            best_rank = year_end_rank
        if best_rank < 1:
            best_rank = 1
        if best_rank > 100:
            best_rank = 100
        s_peak = 1.0 - (best_rank - 1) / 99.0

        success_index_raw = (
            w_rank_n * s_rank + w_weeks_n * s_weeks + w_peak_n * s_peak
        )

        r_out = dict(r)
        r_out["s_rank"] = s_rank
        r_out["s_weeks"] = s_weeks
        r_out["s_peak"] = s_peak
        r_out["success_index_raw"] = success_index_raw
        augmented.append(r_out)

    _log(f"Computed components for {len(augmented)} rows.")
    return augmented


def compute_global_z_and_target(
    rows: List[Dict[str, Any]], k_logistic: float = 1.3
) -> List[Dict[str, Any]]:
    """Add echo_z and EchoTarget_v2 to each row."""
    values: List[float] = []
    for r in rows:
        v = _safe_float(r.get("success_index_raw"))
        if v is not None:
            values.append(v)

    if not values:
        _err("No success_index_raw values; cannot compute z-scores.")
        return rows

    mu = statistics.fmean(values)
    # population std dev
    if len(values) > 1:
        sigma = statistics.pstdev(values, mu=mu)
    else:
        sigma = 0.0

    _log(f"Global success_index_raw mean={mu:.4f}, std={sigma:.4f}")

    if sigma <= 0:
        _warn("Stddev is zero or negative; all z-scores will be 0, targets=0.5")

    # Compute z and logistic target
    for r in rows:
        v = _safe_float(r.get("success_index_raw"))
        if v is None:
            r["echo_z"] = None
            r["EchoTarget_v2"] = None
            continue

        if sigma > 0:
            z = (v - mu) / sigma
        else:
            z = 0.0

        try:
            # logistic mapping to (0,1)
            t = 1.0 / (1.0 + math.exp(-k_logistic * z))
        except OverflowError:
            # extremely large |z|, clamp
            t = 1.0 if z > 0 else 0.0

        r["echo_z"] = z
        r["EchoTarget_v2"] = t

    return rows


def add_deciles(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add echo_decile (1-10) based on EchoTarget_v2 value."""
    # Collect indices of valid targets
    valid: List[Tuple[int, float]] = []
    for idx, r in enumerate(rows):
        t = _safe_float(r.get("EchoTarget_v2"))
        if t is not None:
            valid.append((idx, t))

    if not valid:
        _warn("No valid EchoTarget_v2 values; cannot assign deciles.")
        return rows

    # Sort by target ascending
    valid_sorted = sorted(valid, key=lambda x: x[1])
    n = len(valid_sorted)

    for rank, (idx, _) in enumerate(valid_sorted):
        # rank in [0, n-1]
        # use (rank + 0.5)/n as quantile
        q = (rank + 0.5) / n
        decile = int(q * 10) + 1
        if decile < 1:
            decile = 1
        if decile > 10:
            decile = 10
        rows[idx]["echo_decile"] = decile

    return rows


def write_csv(rows: List[Dict[str, Any]], out_csv: str) -> None:
    if not rows:
        _warn("No rows to write to CSV.")
        return

    # Define a stable column ordering with fallbacks
    preferred_order = [
        "slug",
        "year",
        "year_end_rank",
        "title",
        "artist",
        "best_rank",
        "weeks_on_chart",
        "chart_points",
        "s_rank",
        "s_weeks",
        "s_peak",
        "success_index_raw",
        "echo_z",
        "EchoTarget_v2",
        "echo_decile",
    ]

    # Collect all actual keys present
    keys = set()
    for r in rows:
        keys.update(r.keys())
    # Build fieldnames respecting preferred order
    fieldnames: List[str] = []
    for k in preferred_order:
        if k in keys:
            fieldnames.append(k)
    for k in sorted(keys):
        if k not in fieldnames:
            fieldnames.append(k)

    _log(f"Writing CSV to {out_csv} with {len(rows)} rows and {len(fieldnames)} columns.")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in fieldnames})


def init_targets_table(conn: sqlite3.Connection, reset: bool = False) -> None:
    cur = conn.cursor()
    if reset:
        _log("Reset requested; dropping existing hci_v2_targets table if it exists.")
        cur.execute("DROP TABLE IF EXISTS hci_v2_targets;")

    _log("Ensuring hci_v2_targets schema exists.")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hci_v2_targets (
            slug TEXT PRIMARY KEY,
            year INTEGER,
            year_end_rank INTEGER,
            title TEXT,
            artist TEXT,
            s_rank REAL,
            s_weeks REAL,
            s_peak REAL,
            success_index_raw REAL,
            echo_z REAL,
            EchoTarget_v2 REAL,
            echo_decile INTEGER
        );
        """
    )
    conn.commit()


def infer_slug(row: Dict[str, Any]) -> str:
    # Prefer explicit slug-like columns if present
    for key in ("slug", "core_id", "id"):
        if key in row and row[key]:
            return str(row[key])

    year = row.get("year", "?")
    title = (row.get("title") or "").strip()
    artist = (row.get("artist") or "").strip()
    base = f"{year}_{title}__{artist}"
    # crude normalization
    return base.replace(" ", "_").lower()


def write_targets_table(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> None:
    cur = conn.cursor()
    _log(f"Writing {len(rows)} rows into hci_v2_targets.")
    for r in rows:
        slug = infer_slug(r)
        year = _safe_int(r.get("year"))
        year_end_rank = _safe_int(r.get("year_end_rank") or r.get("year_end_pos") or r.get("rank"))
        title = r.get("title")
        artist = r.get("artist")
        s_rank = _safe_float(r.get("s_rank"))
        s_weeks = _safe_float(r.get("s_weeks"))
        s_peak = _safe_float(r.get("s_peak"))
        success_index_raw = _safe_float(r.get("success_index_raw"))
        echo_z = _safe_float(r.get("echo_z"))
        target = _safe_float(r.get("EchoTarget_v2"))
        decile = _safe_int(r.get("echo_decile"))

        cur.execute(
            """
            INSERT OR REPLACE INTO hci_v2_targets (
                slug,
                year,
                year_end_rank,
                title,
                artist,
                s_rank,
                s_weeks,
                s_peak,
                success_index_raw,
                echo_z,
                EchoTarget_v2,
                echo_decile
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                slug,
                year,
                year_end_rank,
                title,
                artist,
                s_rank,
                s_weeks,
                s_peak,
                success_index_raw,
                echo_z,
                target,
                decile,
            ),
        )

    conn.commit()
    _log("Finished writing hci_v2_targets table.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build EchoTarget_v2 labels from historical_echo.core_spine."
    )
    parser.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help=f"Path to historical_echo SQLite DB (default: {get_historical_echo_db_path()})",
    )
    parser.add_argument(
        "--core-table",
        default="core_spine",
        help="Name of the core spine table (default: core_spine)",
    )
    parser.add_argument(
        "--out-csv",
        default=str(get_hci_v2_targets_csv()),
        help=f"Output CSV path for targets (default: {get_hci_v2_targets_csv()})",
    )
    parser.add_argument(
        "--top-n-per-year",
        type=int,
        default=40,
        help="Assumed top-N per year in core_spine (default: 40)",
    )
    parser.add_argument(
        "--weeks-cap",
        type=int,
        default=0,
        help="Fixed cap for weeks_on_chart; if <=0, derive from percentile (default: 0)",
    )
    parser.add_argument(
        "--weeks-cap-percentile",
        type=float,
        default=0.95,
        help="Percentile used to derive weeks_cap if not fixed (default: 0.95)",
    )
    parser.add_argument(
        "--w-rank",
        type=float,
        default=0.5,
        help="Weight for s_rank in success_index_raw (default: 0.5)",
    )
    parser.add_argument(
        "--w-weeks",
        type=float,
        default=0.3,
        help="Weight for s_weeks in success_index_raw (default: 0.3)",
    )
    parser.add_argument(
        "--w-peak",
        type=float,
        default=0.2,
        help="Weight for s_peak in success_index_raw (default: 0.2)",
    )
    parser.add_argument(
        "--k-logistic",
        type=float,
        default=1.3,
        help="Slope k for logistic mapping of z to EchoTarget_v2 (default: 1.3)",
    )
    parser.add_argument(
        "--reset-targets",
        action="store_true",
        help="Drop and recreate hci_v2_targets table before inserting.",
    )

    args = parser.parse_args()

    _log(f"Opening DB: {args.db}")
    conn = sqlite3.connect(args.db)

    try:
        core_rows = fetch_core_spine_rows(conn, args.core_table)
        if not core_rows:
            _err("No rows found in core_spine; nothing to do.")
            return

        rows_with_components = compute_components(
            core_rows,
            top_n_per_year=args.top_n_per_year,
            weeks_cap=args.weeks_cap,
            weeks_cap_percentile=args.weeks_cap_percentile,
            w_rank=args.w_rank,
            w_weeks=args.w_weeks,
            w_peak=args.w_peak,
        )
        rows_with_targets = compute_global_z_and_target(
            rows_with_components, k_logistic=args.k_logistic
        )
        rows_with_deciles = add_deciles(rows_with_targets)

        # CSV snapshot
        write_csv(rows_with_deciles, args.out_csv)

        # DB table
        init_targets_table(conn, reset=args.reset_targets)
        write_targets_table(conn, rows_with_deciles)

        _log("DONE building EchoTarget_v2 targets.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
