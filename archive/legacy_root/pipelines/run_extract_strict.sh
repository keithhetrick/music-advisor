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

REPO="$(cd "$(dirname "$0")/.." && pwd)"
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

mkdir -p "$OUT_DIR"

base="$(basename "$AUDIO")"
stem="${base%.*}"
ts="$(date -u +%Y%m%d_%H%M%S)"

FEATURES_JSON="$OUT_DIR/${stem}_${ts}.features.json"
SIDECAR_JSON="$OUT_DIR/${stem}_${ts}.sidecar.json"

SIDECAR_CMD="${SIDECAR_CMD_ENV:-$PY_BIN $REPO/tools/tempo_sidecar_runner.py --audio {audio} --out {out}}"

CMD=( "$PY_BIN" "$REPO/tools/ma_audio_features.py"
  --audio "$AUDIO"
  --out "$FEATURES_JSON"
  --no-cache
  --force
  --tempo-backend sidecar
  --require-sidecar
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
