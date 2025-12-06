#!/usr/bin/env bash
set -euo pipefail

# Sync only data/public to S3 (no delete by default).
BUCKET="${BUCKET:-music-advisor-data-external-database-resources}"
PREFIX="${PREFIX:-v1/data/public}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

aws s3 sync "$ROOT/data/public" "s3://${BUCKET}/${PREFIX}" \
  --exclude ".DS_Store" \
  --exclude "*.tmp" \
  --exclude "market_norms/raw/*" \
  --exclude "*.db" \
  --exclude "spine/backfill/*lyrics*"
