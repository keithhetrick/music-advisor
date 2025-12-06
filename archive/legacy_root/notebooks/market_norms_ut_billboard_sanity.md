# Market Norms UT Billboard sanity (November 2025)

Run these snippets in a REPL or notebook after syncing `data/market_norms/market_norms_billboard.db`:

```python
from tools.market_norms_queries import get_top40_for_month, get_latest_chart_dates

# Recent chart dates for Hot 100
latest = get_latest_chart_dates("hot100", limit=8)
print(latest)

# Top 40 Hot 100 for November 2025
hot100_nov25 = get_top40_for_month("hot100", 2025, 11)
print(hot100_nov25.head(), hot100_nov25.shape)

# Top 40 Billboard 200 for November 2025
bb200_nov25 = get_top40_for_month("bb200", 2025, 11)
print(bb200_nov25.head(), bb200_nov25.shape)
```

Expected: non-empty DataFrames with `chart_date` between 2025-11-01 and 2025-11-30, rank ≤ 40.
