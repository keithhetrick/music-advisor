#!/usr/bin/env bash
set -euo pipefail

# Quarterly wrapper for market norms snapshot
# Usage:
#   CSV=path/to/features.csv REGION=US TIER=Hot100Top40 VERSION=2025-Q4 ./scripts/build_market_norms_quarter.sh

CSV="${CSV:?CSV is required}"
REGION="${REGION:-US}"
TIER="${TIER:-Hot100Top40}"
VERSION="${VERSION:-$(date +%Y-Q%q)}"

python scripts/build_market_norms_snapshot.py \
  --csv "$CSV" \
  --region "$REGION" \
  --tier "$TIER" \
  --version "$VERSION" \
  --out data/market_norms
