#!/usr/bin/env python3
"""
Export a Billboard chart to CSV (title, artist, year, spotify_id blank).

Uses the unofficial billboard.py package (scrapes billboard.com).
**Check Billboard terms of service before use.**

Usage:
  python scripts/export_billboard_chart.py --chart hot-100 --date 2024-12-31 --out /tmp/billboard_hot100_2024-12-31.csv
  python scripts/export_billboard_chart.py --chart hot-100 --out /tmp/billboard_hot100_latest.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime
from pathlib import Path

try:
    import billboard  # type: ignore
except ImportError as exc:
    raise SystemExit("billboard.py is required: pip install billboard.py") from exc


def main() -> None:
    ap = argparse.ArgumentParser(description="Export Billboard chart to CSV (title, artist, year, spotify_id blank).")
    ap.add_argument("--chart", default="hot-100", help="Billboard chart name (default hot-100).")
    ap.add_argument("--date", default=None, help="Chart date (YYYY-MM-DD). If omitted, uses latest.")
    ap.add_argument("--out", required=True, help="Output CSV path.")
    args = ap.parse_args()

    chart_date = args.date
    chart = billboard.ChartData(args.chart, date=chart_date)
    entries = []
    for e in chart:
        entries.append(
            {
                "title": e.title,
                "artist": e.artist,
                "year": datetime.date.today().year,
                "spotify_id": "",
            }
        )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "artist", "year", "spotify_id"])
        writer.writeheader()
        writer.writerows(entries)
    print(f"[DONE] Wrote Billboard chart CSV -> {out_path} (rows={len(entries)})")


if __name__ == "__main__":
    main()
