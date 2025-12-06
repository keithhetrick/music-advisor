#!/usr/bin/env bash
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/lib_security.sh"

# Clear feature cache contents with an explicit prompt.
# Usage: scripts/clear_feature_cache.sh [cache_dir]

CACHE_DIR="${1:-.ma_cache}"

if [[ ! -d "$CACHE_DIR" ]]; then
  echo "[WARN] Cache dir not found: $CACHE_DIR"
  exit 0
fi

echo "[INFO] Cache directory: $CACHE_DIR"
du -sh "$CACHE_DIR" 2>/dev/null || true

read -r -p "Delete all contents of '$CACHE_DIR'? [y/N] " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
  require_safe_subpath "$(pwd)" "$CACHE_DIR" || exit $?
  rm -rf "${CACHE_DIR:?}/"*
  echo "[OK] Cleared cache contents in $CACHE_DIR"
else
  echo "[SKIP] Cache not cleared."
fi
