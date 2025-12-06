#!/usr/bin/env bash
set -euo pipefail

# One-shot public bootstrap for users:
# - Downloads manifest-backed public assets
# - Builds a SQLite spine DB from public CSVs (unless --no-db)
#
# Usage:
#   infra/scripts/full_public_bootstrap.sh
#   infra/scripts/full_public_bootstrap.sh --data-root /path/to/data --manifest /custom/manifest.json --db-out /tmp/spine.db
#
# Flags:
#   --manifest PATH    Use a custom manifest (default: infra/scripts/data_manifest.json)
#   --data-root PATH   Override MA_DATA_ROOT for the run (default: $MA_DATA_ROOT or ./data)
#   --db-out PATH      Custom SQLite output (default: <data_root>/public/spine/spine_public.db)
#   --no-db            Skip DB build (only download public assets)
#   --force            Overwrite existing DB if present (default: true)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$ROOT/infra/scripts/data_manifest.json"
DATA_ROOT="${MA_DATA_ROOT:-$ROOT/data}"
DB_OUT=""
DO_DB=1
DB_FORCE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)
      MANIFEST="$2"; shift 2;;
    --data-root)
      DATA_ROOT="$2"; shift 2;;
    --db-out)
      DB_OUT="$2"; shift 2;;
    --no-db)
      DO_DB=0; shift;;
    --force)
      DB_FORCE=1; shift;;
    --help|-h)
      sed -n '1,30p' "$0"; exit 0;;
    *)
      echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

echo "[bootstrap] manifest: $MANIFEST"
echo "[bootstrap] data root: $DATA_ROOT"
python3 "$ROOT/infra/scripts/data_bootstrap.py" --manifest "$MANIFEST"

if [[ "$DO_DB" -eq 1 ]]; then
  DB_OUT="${DB_OUT:-$DATA_ROOT/public/spine/spine_public.db}"
  echo "[bootstrap] building SQLite spine DB -> $DB_OUT"
  python3 "$ROOT/infra/scripts/build_public_spine_db.py" \
    --data-root "$DATA_ROOT" \
    --out "$DB_OUT" \
    ${DB_FORCE:+--force}
else
  echo "[bootstrap] skipping DB build (--no-db)"
fi

echo "[bootstrap] done"
