#!/usr/bin/env bash
set -euo pipefail

# Strict extractor wrapper:
# - Requires sidecar (no silent librosa fallback)
# - Uses sidecar confidence bounds if provided via env TEMPO_CONF_LOWER/UPPER
# - Uses MA_SIDECAR_CMD if set; otherwise defaults to tools/tempo_sidecar_runner.py
# - Disables cache for fresh extraction
#
# Usage:
#   scripts/run_extract_strict.sh --audio /path/to/file.wav --out-dir /path/to/output [--keep-beats]
#
# Outputs:
#   <out-dir>/<stem>_<ts>.features.json
#   <out-dir>/<stem>_<ts>.sidecar.json

AUDIO=""
OUT_DIR=""
KEEP_BEATS=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --audio)
      AUDIO="$2"; shift 2;;
    --out-dir)
      OUT_DIR="$2"; shift 2;;
    --keep-beats)
      KEEP_BEATS=1; shift;;
    *)
      echo "Unknown arg: $1" >&2; exit 64;;
  esac
done

if [[ -z "$AUDIO" || -z "$OUT_DIR" ]]; then
  echo "Usage: $0 --audio <file> --out-dir <dir> [--keep-beats]" >&2
  exit 64
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
# Ensure common binary roots (ffmpeg/ffprobe) are discoverable even under Automator
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
PY_BIN="${PY_BIN:-$REPO/.venv/bin/python}"
SIDECAR_CMD_ENV="${MA_SIDECAR_CMD:-}"
CONF_LOWER="${TEMPO_CONF_LOWER:-}"
CONF_UPPER="${TEMPO_CONF_UPPER:-}"

if [[ ! -x "$PY_BIN" ]]; then
  echo "[ERR] Python venv not found: $PY_BIN" >&2
  exit 1
fi

if [[ ! -f "$AUDIO" ]]; then
  echo "[ERR] Audio file not found: $AUDIO" >&2
  exit 1
fi

require_safe_subpath "$REPO/features_output" "$OUT_DIR" || { echo "[ERR] OUT_DIR outside features_output"; exit 64; }
mkdir -p "$OUT_DIR"

base="$(basename "$AUDIO")"
stem="${base%.*}"
ts="$(date -u +%Y%m%d_%H%M%S)"

FEATURES_JSON="$OUT_DIR/${stem}_${ts}.features.json"
SIDECAR_JSON="$OUT_DIR/${stem}_${ts}.sidecar.json"

SIDECAR_CMD="${SIDECAR_CMD_ENV:-"$PY_BIN $REPO/tools/tempo_sidecar_runner.py --audio {audio} --out {out}"}"
# Allow overriding sidecar timeout via env; default to 120s for stability. Passed via env so ma_audio_features picks it up.
SIDECAR_TIMEOUT="${TEMPO_SIDECAR_TIMEOUT:-120}"
export SIDECAR_TIMEOUT_SECONDS="$SIDECAR_TIMEOUT"

CMD=( "$PY_BIN" "$REPO/tools/ma_audio_features.py"
  --audio "$AUDIO"
  --out "$FEATURES_JSON"
  --no-cache
  --force
  --tempo-backend sidecar
  --tempo-sidecar-json-out "$SIDECAR_JSON"
  --tempo-sidecar-cmd "$SIDECAR_CMD"
)

if [[ -n "$CONF_LOWER" && -n "$CONF_UPPER" ]]; then
  CMD+=(--tempo-sidecar-conf-lower "$CONF_LOWER" --tempo-sidecar-conf-upper "$CONF_UPPER")
fi

if [[ "$KEEP_BEATS" -eq 0 ]]; then
  CMD+=(--tempo-sidecar-drop-beats)
fi

echo "[strict-extract] ${CMD[*]}"
exec "${CMD[@]}"
