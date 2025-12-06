#!/bin/bash
set -euo pipefail
# Batch normalize an entire calibration tree to EXACT -10 LUFS / -1 dBTP

SRC_ROOT="${1:-}"
DST_ROOT="${2:-}"
TARGET="${3:--10}"
TP="${4:--1}"
LRA="${5:-11}"

if [[ -z "$SRC_ROOT" || -z "$DST_ROOT" ]]; then
  echo "usage: $0 <SRC_ROOT/audio> <DST_ROOT/audio_norm> [TARGET=-10] [TP=-1] [LRA=11]"
  exit 2
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[error] ffmpeg not found"; exit 3
fi

# Ensure python script is executable
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_NORM="$SCRIPT_DIR/loudnorm_exact.py"
chmod +x "$PY_NORM"

mapfile -t FILES < <(find "$SRC_ROOT" -type f -name "*.wav" -print | sort)

echo "[norm] total WAV files: ${#FILES[@]}"
for src in "${FILES[@]}"; do
  rel="${src#"$SRC_ROOT"/}"
  dst="$DST_ROOT/$rel"
  echo "[norm] $rel"
  python3 "$PY_NORM" --in "$src" --out "$dst" --target "$TARGET" --tp "$TP" --lra "$LRA" || {
    echo "[warn] failed: $rel"
    continue
  }
done
echo "[norm] done."
