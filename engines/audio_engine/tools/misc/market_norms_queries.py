"""
Query helpers for market_norms Billboard DB.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ma_config.paths import get_data_root

DEFAULT_DB = get_data_root() / "market_norms" / "market_norms_billboard.db"


def _connect(db: Union[str, Path]) -> sqlite3.Connection:
    return sqlite3.connect(str(db))


def get_week_chart(chart: str, chart_date: Union[str, pd.Timestamp], top_k: Optional[int] = None, db: Union[str, Path] = DEFAULT_DB) -> pd.DataFrame:
    table = "hot100_weekly" if chart.lower() in ("hot100", "hot_100") else "bb200_weekly"
    chart_date_str = str(chart_date)
    with _connect(db) as conn:
        df = pd.read_sql_query(
            f"SELECT * FROM {table} WHERE chart_date = ? ORDER BY rank ASC",
            conn,
            params=(chart_date_str,),
            parse_dates=["chart_date"],
        )
    if top_k:
        df = df[df["rank"] <= top_k]
    return df


def get_top40_for_week(chart: str, chart_date: Union[str, pd.Timestamp], db: Union[str, Path] = DEFAULT_DB) -> pd.DataFrame:
    return get_week_chart(chart, chart_date, top_k=40, db=db)


def get_month_charts(chart: str, year: int, month: int, top_k: Optional[int] = None, db: Union[str, Path] = DEFAULT_DB) -> pd.DataFrame:
    table = "hot100_weekly" if chart.lower() in ("hot100", "hot_100") else "bb200_weekly"
    with _connect(db) as conn:
        df = pd.read_sql_query(
            f"SELECT * FROM {table} WHERE strftime('%Y', chart_date) = ? AND strftime('%m', chart_date) = ? ORDER BY chart_date ASC, rank ASC",
            conn,
            params=(str(year), f"{month:02d}"),
            parse_dates=["chart_date"],
        )
    if top_k:
        df = df[df["rank"] <= top_k]
    return df


def get_top40_for_month(chart: str, year: int, month: int, db: Union[str, Path] = DEFAULT_DB) -> pd.DataFrame:
    return get_month_charts(chart, year, month, top_k=40, db=db)


def get_latest_chart_dates(chart: str, limit: int = 8, db: Union[str, Path] = DEFAULT_DB) -> pd.DataFrame:
    table = "hot100_weekly" if chart.lower() in ("hot100", "hot_100") else "bb200_weekly"
    with _connect(db) as conn:
        df = pd.read_sql_query(
            f"SELECT DISTINCT chart_date FROM {table} ORDER BY chart_date DESC LIMIT ?",
            conn,
            params=(limit,),
            parse_dates=["chart_date"],
        )
    return df
