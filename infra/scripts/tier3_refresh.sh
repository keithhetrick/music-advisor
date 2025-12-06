#!/usr/bin/env bash
# Rebuild Tier 3 (EchoTier_3_YearEnd_Top200_Modern) end-to-end from local sources.
# This is a convenience wrapper; Tier 1/Tier 2 remain untouched.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="${HISTORICAL_ECHO_DB:-$REPO/data/historical_echo/historical_echo.db}"
YEAR_END_TOP200="$REPO/data/yearend_hot100/yearend_hot100_top200_1985_2024.csv"

echo "[TIER3] Deriving Year-End Top 200 (points from weekly Hot 100)…"
python3 "$REPO/tools/spine/build_yearend_top200_from_weekly_hot100.py" \
  --weekly-csv "$REPO/data/external/weekly/ut_hot_100_1958_present.csv" \
  --out "$YEAR_END_TOP200" \
  --year-min 1985 \
  --year-max 2024

echo "[TIER3] Building lanes CSV and importing to SQLite…"
python3 "$REPO/tools/spine/build_spine_master_tier3_modern_lanes_v1.py" \
  --input-csv "$YEAR_END_TOP200" \
  --out "$REPO/data/spine/spine_master_tier3_modern_lanes_v1.csv" \
  --db "$DB" \
  --reset

echo "[TIER3] Backfill from existing tiers (Tier1/2 overlaps)…"
python3 "$REPO/tools/spine/backfill_tier3_from_existing_tiers.py" \
  --db "$DB"

echo "[TIER3] Backfill from external offline audio sources…"
python3 "$REPO/tools/spine/backfill_tier3_from_external_audio.py" \
  --db "$DB"

echo "[TIER3] Coverage after refresh:"
sqlite3 "$DB" "SELECT COUNT(*) AS total, SUM(has_audio <> 0) AS with_audio FROM spine_master_tier3_modern_lanes_v1;"
sqlite3 "$DB" "SELECT year, COUNT(*) AS tier3_tracks, SUM(has_audio <> 0) AS with_audio FROM spine_master_tier3_modern_lanes_v1 GROUP BY year ORDER BY year;"

echo "[TIER3] Done."
