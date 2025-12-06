#!/bin/bash
set -euo pipefail
# Run automator.sh on every WAV under a root (e.g., CALIB_ROOT/audio_norm)
# It writes packs under per-anchor _packs/ and logs under _logs/

ROOT="${1:-}"
if [[ -z "${ROOT}" ]]; then
  echo "usage: $0 <ROOT folder containing anchor subfolders with .wav files>" >&2
  exit 2
fi

# sanity
if [[ ! -d "$ROOT" ]]; then
  echo "[err] not a directory: $ROOT" >&2
  exit 2
fi

# Resolve script dir so we can call automator.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOMATOR="$(cd "$SCRIPT_DIR/.." && pwd)/automator.sh"

# iterate anchors (first-level subdirs)
find "$ROOT" -mindepth 1 -maxdepth 1 -type d | sort | while IFS= read -r ANCHOR_DIR; do
  anchor="$(basename "$ANCHOR_DIR")"
  echo "=== Automating anchor: $anchor ==="

  # Per-anchor outputs co-located with audio for calibration
  export ARCHIVE_ROOT="$ANCHOR_DIR/_packs"
  export LOG_ROOT="$ANCHOR_DIR/_logs"
  mkdir -p "$ARCHIVE_ROOT" "$LOG_ROOT"

  # Feed every wav in this anchor
  find "$ANCHOR_DIR" -type f -name "*.wav" | sort | while IFS= read -r WAV; do
    echo "[auto] $anchor :: $(basename "$WAV")"
    "$AUTOMATOR" "$WAV"
  done
done

echo "✓ automator_batch complete."
