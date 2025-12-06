#!/bin/bash
set -euo pipefail
# Batch normalize a whole calibration tree using pyloudnorm (measure) + ffmpeg (apply)
# Compatible with macOS bash 3.2 (no 'mapfile').

SRC_ROOT="${1:-}"
DST_ROOT="${2:-}"
TARGET="${3:--10}"
TP="${4:--1}"
TOL="${5:-0.3}"
MAXIT="${6:-2}"

if [[ -z "${SRC_ROOT}" || -z "${DST_ROOT}" ]]; then
  echo "usage: $0 <SRC_ROOT/audio> <DST_ROOT/audio_norm> [TARGET=-10] [TP=-1] [TOL=0.3] [MAXIT=2]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_NORM="$SCRIPT_DIR/normalize_to_lufs.py"
chmod +x "$PY_NORM"

count=$(find "$SRC_ROOT" -type f -name "*.wav" | wc -l | tr -d ' ')
echo "[norm] total WAV files: ${count}"

# Iterate files in a portable way
find "$SRC_ROOT" -type f -name "*.wav" | sort | while IFS= read -r src; do
  rel="${src#"$SRC_ROOT"/}"
  dst="$DST_ROOT/$rel"
  echo "[norm] $rel"
  mkdir -p "$(dirname "$dst")"
  if ! python3 "$PY_NORM" --in "$src" --out "$dst" --target "$TARGET" --tp "$TP" --tolerance "$TOL" --max-iters "$MAXIT"; then
    echo "[warn] failed: $rel" >&2
  fi
done

echo "[norm] done."
