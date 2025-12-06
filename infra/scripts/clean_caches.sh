#!/usr/bin/env bash
set -euo pipefail

# Clean common local caches and temp artifacts.
# Safe to run; only removes generated/cache files, never tracked source.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "[clean] removing __pycache__ dirs and *.pyc files..."
find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "[clean] removing tool caches..."
rm -rf tools/.ma_cache 2>/dev/null || true

echo "[clean] removing local lint/test caches..."
rm -rf .ruff_cache .mypy_cache .pytest_cache hosts/*/.ruff_cache hosts/*/.mypy_cache hosts/*/.pytest_cache 2>/dev/null || true

echo "[clean] done."
