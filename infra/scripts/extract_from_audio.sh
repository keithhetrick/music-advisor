#!/bin/bash
# scripts/extract_from_audio.sh — minimal extractor shim
# Creates a YYYY/MM/DD/<slug>/ folder under $OUTPUT_ROOT with a stub .pack.json and .client.txt
# so the pipeline can run immediately. Replace the "REAL EXTRACTOR" section later.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AUDIO="${1:-}"
[ -f "$AUDIO" ] || { echo "ERROR: audio not found: $AUDIO" >&2; exit 66; }

# OUTPUT_ROOT is passed in by the wrapper; default if missing
OUTPUT_ROOT="${OUTPUT_ROOT:-$HOME/music-advisor/features_output}"

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

stem="$(basename "$AUDIO")"; stem="${stem%.*}"
slug="$(slugify "$stem")"
today="$(date +%Y/%m/%d)"
ts="$(date +%Y%m%d_%H%M%S)"

outdir="$OUTPUT_ROOT/$today/${slug}"
mkdir -p "$outdir"
require_safe_subpath "$OUTPUT_ROOT" "$outdir" || { echo "ERROR: outdir outside OUTPUT_ROOT"; exit 64; }

# ---- REAL EXTRACTOR (audio features + sidecar) ----
# This uses the strict extractor to generate *.features.json + *.sidecar.json
# so builder_cli can assemble a richer pack/client downstream.
PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/src:${PYTHONPATH:-}"
export PYTHONPATH

"${REPO_ROOT}/scripts/run_extract_strict.sh" \
  --audio "$AUDIO" \
  --out-dir "$outdir"

# Assemble pack + client from whatever artifacts exist (features/merged/beatlink)
"${REPO_ROOT}/.venv/bin/python" \
  "${REPO_ROOT}/tools/builder_cli.py" \
  --audio "$AUDIO" \
  --output-root "$OUTPUT_ROOT"

# Emit a machine-readable hint for the wrapper
echo "OUTDIR=$outdir"
