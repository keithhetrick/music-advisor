# Market Norms — UT Billboard (research spine)

- Source: UT Austin `rwd-billboard-data` (MIT licensed repo; underlying chart data is Billboard IP; internal research/advisory use only).
- Hot 100 CSV: `https://raw.githubusercontent.com/utdata/rwd-billboard-data/main/data-out/hot-100-current.csv`
- Billboard 200 CSV: `https://raw.githubusercontent.com/utdata/rwd-billboard-data/main/data-out/billboard-200-current.csv`
- Config: `config/market_norms_ut_billboard.yml`
- DB (SQLite): `data/market_norms/market_norms_billboard.db`
- Sync script: `tools/market_norms_ut_billboard_sync.py` (wrapper: `scripts/market_norms_sync_ut_billboard.sh`)
- Query helpers: `tools/market_norms_queries.py`

## Usage

Sync (from repo root):

```bash
./scripts/market_norms_sync_ut_billboard.sh
# or specify a local clone of rwd-billboard-data:
# SRC_PATH=/path/to/rwd-billboard-data ./scripts/market_norms_sync_ut_billboard.sh
```

Current ingest (Dec 2025) succeeds:

```bash
[market_norms_ut_billboard] synced Hot 100 rows: 351400
[market_norms_ut_billboard] synced Billboard 200 rows: 612291
DB -> data/market_norms/market_norms_billboard.db
```

Query examples (Python):

```python
from tools.market_norms_queries import get_top40_for_week, get_top40_for_month, get_latest_chart_dates

# Top 40 Hot 100 for a specific week
df = get_top40_for_week("hot100", "2025-11-15")

# Top 40 Hot 100 for November 2025
df_month = get_top40_for_month("hot100", 2025, 11)

# Recent chart dates
latest = get_latest_chart_dates("hot100", limit=8)
```

Export a top-40 slice for feature enrichment:

```bash
python tools/export_billboard_top40.py \
  --db data/market_norms/market_norms_billboard.db \
  --chart hot100 --year-month 2025 11 \
  --out /tmp/hot100_top40_2025_11.csv
```

Or for a specific chart week:

```bash
python tools/export_billboard_top40.py \
  --db data/market_norms/market_norms_billboard.db \
  --chart bb200 --chart-date 2025-11-29 \
  --out /tmp/bb200_top40_2025-11-29.csv
```

## Notes

- This is a research/advisory layer; swap to a licensed feed (e.g., Luminate) later without changing the schema/API.
- Snapshot covers Hot 100 (1958→current) and Billboard 200 (1967→current) as published in the UT repo.
- Ensure `config/market_norms_ut_billboard.yml` is kept up to date (optionally pin a commit hash if you clone the UT repo).
