#!/usr/bin/env zsh
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 /path/to/audio.file [out.json]" >&2
  exit 1
fi

AUDIO="$1"
OUT="${2:-/tmp/ma_features_smoke.json}"

if [ ! -f "$AUDIO" ]; then
  echo "Audio file not found: $AUDIO" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
if [ -z "$PYTHON_BIN" ]; then
  echo "python3 not found on PATH" >&2
  exit 1
fi

echo "== Pipeline smoke =="
echo "Audio: $AUDIO"
echo "Out:   $OUT"

PYTHONPATH="$ROOT" "$PYTHON_BIN" "$ROOT/engines/audio_engine/tools/cli/ma_audio_features.py" \
  --audio "$AUDIO" \
  --out "$OUT"

echo "Wrote $OUT"
