#!/usr/bin/env python3
"""
Quick TTC corpus diagnostics.

Reads a TTC reference CSV/JSON and prints distribution summaries (mean/median/percentiles)
and decade buckets (1980s, 1990s, 2000s, 2010s, 2020s).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

import statistics


def _load_rows(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text())
            return [dict(row) for row in data if isinstance(row, dict)]
        except Exception:
            return []
    rows: List[Dict[str, object]] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(dict(row))
    except Exception:
        return []
    return rows


def _safe_float(val: object) -> Optional[float]:
    try:
        if val is None or val == "":
            return None
        return float(val)
    except Exception:
        return None


def _bucket_decade(year: Optional[int]) -> Optional[str]:
    if year is None:
        return None
    decade = (year // 10) * 10
    return f"{decade}s"


def summarize(rows: List[Dict[str, object]]) -> str:
    ttcs = [_safe_float(r.get("ttc_seconds")) for r in rows]
    ttcs = [t for t in ttcs if t is not None]
    if not ttcs:
        return "No TTC rows to summarize."
    lines: List[str] = []
    lines.append(f"Total rows: {len(rows)} (with TTC: {len(ttcs)})")
    lines.append(f"Mean TTC: {statistics.mean(ttcs):.2f}s")
    lines.append(f"Median TTC: {statistics.median(ttcs):.2f}s")
    for pct in (0.1, 0.25, 0.75, 0.9):
        idx = int(pct * (len(ttcs) - 1))
        ttcs_sorted = sorted(ttcs)
        lines.append(f"P{int(pct*100)} TTC: {ttcs_sorted[idx]:.2f}s")
    decade_buckets: Dict[str, List[float]] = {}
    for row, ttc in zip(rows, ttcs):
        year_val = row.get("year")
        try:
            year = int(year_val) if year_val is not None else None
        except Exception:
            year = None
        bucket = _bucket_decade(year)
        if not bucket:
            continue
        decade_buckets.setdefault(bucket, []).append(ttc)
    if decade_buckets:
        lines.append("")
        lines.append("Decade TTC means:")
        for bucket, vals in sorted(decade_buckets.items()):
            lines.append(f"  {bucket}: {statistics.mean(vals):.2f}s (n={len(vals)})")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Compute TTC corpus stats.")
    ap.add_argument("--corpus", required=True, help="Path to ttc_reference CSV/JSON.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    rows = _load_rows(Path(args.corpus).expanduser())
    print(summarize(rows))


if __name__ == "__main__":
    main()
