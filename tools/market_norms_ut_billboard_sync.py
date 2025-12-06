#!/usr/bin/env python3
"""
Sync UT Austin rwd-billboard-data (Hot 100 + Billboard 200) into a local SQLite DB.

Usage:
  python tools/market_norms_ut_billboard_sync.py \
    [--source-path /path/to/rwd-billboard-data] \
    [--db <DATA_ROOT>/market_norms/market_norms_billboard.db]

Notes:
- If --source-path is not provided, the script fetches the CSVs from GitHub raw URLs.
- This is for internal research/advisory use only. Underlying chart data remains Billboard IP.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import Date, Integer, MetaData, String, create_engine

from ma_config.paths import get_data_root


HOT100_REL = Path("data-out/hot-100-current.csv")
BB200_REL = Path("data-out/billboard-200-current.csv")
HOT100_DEFAULT_URL = "https://raw.githubusercontent.com/utdata/rwd-billboard-data/main/data-out/hot-100-current.csv"
BB200_DEFAULT_URL = "https://raw.githubusercontent.com/utdata/rwd-billboard-data/main/data-out/billboard-200-current.csv"

DEFAULT_DB = get_data_root() / "market_norms" / "market_norms_billboard.db"


def load_chart_csv(source_path: Optional[Path], rel_path: Path, fallback_url: str) -> pd.DataFrame:
    if source_path:
        csv_path = source_path / rel_path
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found at {csv_path}")
        return pd.read_csv(csv_path)
    return pd.read_csv(fallback_url)


def normalize(df: pd.DataFrame, chart_name: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    # Map flexible column names
    col_map = {
        "chart_week": "chart_date",
        "chartdate": "chart_date",
        "chart_date": "chart_date",
        "weekid": "chart_date",
        "date": "chart_date",
        "song": "title",
        "title": "title",
        "song_name": "title",
        "artist": "artist",
        "performer": "artist",
        "rank": "rank",
        "current_week": "rank",
        "peak_pos": "peak_pos",
        "peak": "peak_pos",
        "last_pos": "last_pos",
        "last_week": "last_pos",
        "wks_on_chart": "weeks_on_chart",
        "weeks_on_chart": "weeks_on_chart",
        "weeks": "weeks_on_chart",
        "is_reentry": "is_reentry",
        "reentry": "is_reentry",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Required fields with defaults
    df["chart_name"] = chart_name
    if "chart_date" in df.columns:
        df["chart_date"] = pd.to_datetime(df["chart_date"], errors="coerce").dt.date
    else:
        df["chart_date"] = pd.NaT

    if "rank" not in df.columns:
        raise KeyError("rank column not found in source CSV")
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce").astype("Int64")
    df["peak_pos"] = pd.to_numeric(df.get("peak_pos"), errors="coerce").astype("Int64")
    df["last_pos"] = pd.to_numeric(df.get("last_pos"), errors="coerce").astype("Int64")
    df["weeks_on_chart"] = pd.to_numeric(df.get("weeks_on_chart"), errors="coerce").astype("Int64")

    if "title" not in df.columns:
        df["title"] = ""
    df["title"] = df["title"].fillna("")
    if "artist" not in df.columns:
        df["artist"] = ""
    df["artist"] = df["artist"].fillna("")

    for col in ("peak_pos", "last_pos", "weeks_on_chart", "is_reentry"):
        if col not in df.columns:
            df[col] = None
        df[col] = df[col].where(pd.notnull(df[col]), None)

    df = df.dropna(subset=["chart_date", "rank"])

    return df[["chart_name", "chart_date", "rank", "title", "artist", "peak_pos", "last_pos", "weeks_on_chart", "is_reentry"]]


def prepare_tables(metadata: MetaData):
    return {
        "chart_name": String,
        "chart_date": Date,
        "rank": Integer,
        "title": String,
        "artist": String,
        "peak_pos": Integer,
        "last_pos": Integer,
        "weeks_on_chart": Integer,
        "is_reentry": String,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync UT Billboard charts into SQLite.")
    ap.add_argument("--source-path", default=None, help="Path to local rwd-billboard-data clone (optional).")
    ap.add_argument("--db", default=str(DEFAULT_DB), help=f"Path to SQLite DB (default {DEFAULT_DB}).")
    args = ap.parse_args()

    source_path = Path(args.source_path).resolve() if args.source_path else None
    db_path = Path(args.db).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    hot100_df = load_chart_csv(source_path, HOT100_REL, HOT100_DEFAULT_URL)
    bb200_df = load_chart_csv(source_path, BB200_REL, BB200_DEFAULT_URL)

    hot100_norm = normalize(hot100_df, "hot100")
    bb200_norm = normalize(bb200_df, "billboard200")

    engine = create_engine(f"sqlite:///{db_path}")
    dtypes = prepare_tables(MetaData())
    hot100_norm.to_sql("hot100_weekly", engine, if_exists="replace", index=False, dtype=dtypes)
    bb200_norm.to_sql("bb200_weekly", engine, if_exists="replace", index=False, dtype=dtypes)

    print(f"[market_norms_ut_billboard] synced Hot 100 rows: {len(hot100_norm)}")
    print(f"[market_norms_ut_billboard] synced Billboard 200 rows: {len(bb200_norm)}")
    print(f"[market_norms_ut_billboard] DB -> {db_path}")


if __name__ == "__main__":
    main()
