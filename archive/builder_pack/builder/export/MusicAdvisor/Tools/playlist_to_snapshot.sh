#!/usr/bin/env bash
# playlist_to_snapshot.sh — convert CSV export to snapshot JSON (no APIs)

set -euo pipefail
if [ $# -lt 2 ]; then
  echo "Usage: $0 <csv_path> <TagLike_HitPulse_2025_11_A>"
  exit 1
fi

CSV="$1"
TAG="$2"
OUT="imports/${TAG}.json"

# Adjust column mappings if your exporter names differ
python3 tools/csv_to_trendjson.py "$CSV" \
  --playlist "$TAG" \
  -o "$OUT" \
  --col-title track_name \
  --col-artist artist_name \
  --col-url track_url \
  --verbose

echo ""
echo "✓ Snapshot JSON ready: $OUT"
echo ""
echo "Paste these in the MusicAdvisor GPT:"
echo "/trend import file=./$OUT"
echo "/trend snapshot finalize name=${TAG/_/-} source=import"
echo "/datahub reload"
