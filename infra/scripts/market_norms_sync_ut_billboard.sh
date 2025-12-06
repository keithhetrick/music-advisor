#!/usr/bin/env bash
# Sync UT Billboard charts into local SQLite DB.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${DB_PATH:-$ROOT/data/market_norms/market_norms_billboard.db}"
SRC_PATH="${SRC_PATH:-}"

cd "$ROOT"
python3 tools/market_norms_ut_billboard_sync.py ${SRC_PATH:+--source-path "$SRC_PATH"} --db "$DB_PATH"
