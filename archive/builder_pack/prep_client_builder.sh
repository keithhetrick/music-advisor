#!/usr/bin/env bash
# Prep a ZIP for builder ingestion (client-only helpers).
# Run from vendor/MusicAdvisor_BuilderPack. Outputs builder_export_MusicAdvisor_client.zip by default.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/builder/export/MusicAdvisor"
OUT="${1:-$ROOT/builder_export_MusicAdvisor_client.zip}"

if [[ ! -d "$SRC" ]]; then
  echo "[ERR] Source folder not found: $SRC" >&2
  exit 1
fi

echo "[INFO] Writing ZIP -> $OUT"
cd "$ROOT"

zip -r -9 "$OUT" "builder/export/MusicAdvisor" \
  -x "*/Tests/*" \
     "*__pycache__/*" \
     "*.pyc" "*.pyo" \
     "*/.DS_Store" \
     "*/.venv/*" \
     "*/out/*" \
     "*/out.json" \
     "*/mock_*.txt" \
     "*/mock_*.json"

echo "[DONE] Created $OUT"
