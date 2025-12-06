#!/usr/bin/env bash
set -euo pipefail

# ---- Basic PATH so Automator sees Homebrew + system tools ----
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# ---- Repo + Python config ----
REPO="${REPO:-$HOME/music-advisor}"
PY_BIN="${PY_BIN:-$REPO/.venv/bin/python}"
SIDECAR_CMD_ENV="${MA_SIDECAR_CMD:-}"
# Default confidence bounds to the calibrated Essentia window unless overridden
CONF_LOWER="${TEMPO_CONF_LOWER:-0.9}"
CONF_UPPER="${TEMPO_CONF_UPPER:-3.6}"

OUT_ROOT="$REPO/features_output"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERR] Required tool '$1' not found on PATH." >&2
    exit 1
  fi
}

# These are mostly sanity checks; the extractor itself uses Python + libs.
need ffprobe
need jq

if [[ ! -x "$PY_BIN" ]]; then
  echo "[ERR] Python venv not found or not executable: $PY_BIN" >&2
  exit 1
fi

# Optional: fast dependency preflight for sidecar
if [[ -x "$REPO/scripts/check_sidecar_deps.sh" ]]; then
  PY_BIN="$PY_BIN" "$REPO/scripts/check_sidecar_deps.sh" || exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "[ERR] Drag & drop one or more audio files onto this workflow." >&2
  exit 1
fi

FAIL_ON_CLIP_DBFS="${FAIL_ON_CLIP_DBFS:-}"

yyyy="$(date +%Y)"
mm="$(date +%m)"
dd="$(date +%d)"
CLIP_ARGS=()

for IN_PATH in "$@"; do
  if [[ ! -f "$IN_PATH" ]]; then
    echo "[WARN] Skipping non-file: $IN_PATH"
    continue
  fi

  base="$(basename "$IN_PATH")"
  stem="${base%.*}"
  ts="$(date -u +%Y%m%d_%H%M%S)"

  OUT_DIR="$OUT_ROOT/$yyyy/$mm/$dd/$stem"
  mkdir -p "$OUT_DIR"

  echo "== Automator :: $stem @ $ts =="
 echo "→ Dropped path: $IN_PATH"
 echo "→ Output folder: $OUT_DIR"

 FEATURES_JSON="$OUT_DIR/${stem}_${ts}.features.json"
 SIDECAR_JSON="$OUT_DIR/${stem}_${ts}.sidecar.json"
  MERGED_JSON="$OUT_DIR/${stem}_${ts}.merged.json"
  CLIENT_TXT="$OUT_DIR/${stem}.client.txt"
  CLIENT_JSON="$OUT_DIR/${stem}.client.json"
  if [[ -n "$SIDECAR_CMD_ENV" ]]; then
    SIDECAR_CMD="$SIDECAR_CMD_ENV"
  else
    SIDECAR_CMD="$PY_BIN $REPO/tools/tempo_sidecar_runner.py --audio {audio} --out {out}"
  fi

  # 1) Core audio features (non-null, SciPy shim handled inside tool)
  if [[ -x "$REPO/tools/ma_audio_features.py" ]]; then
    echo "[features] tools/ma_audio_features.py"
    CMD=( "$PY_BIN" "$REPO/tools/ma_audio_features.py"
      --audio "$IN_PATH"
      --out "$FEATURES_JSON"
      --cache-dir "$REPO/.ma_cache"
      --no-cache
      --force
      --clip-peak-threshold 0.999
      --silence-ratio-threshold 0.9
      --low-level-dbfs-threshold -40
      --tempo-backend sidecar
      --require-sidecar
      --tempo-sidecar-json-out "$SIDECAR_JSON"
      --tempo-sidecar-cmd "$SIDECAR_CMD"
    )
    if [[ -n "$CONF_LOWER" && -n "$CONF_UPPER" ]]; then
      CMD+=(--tempo-sidecar-conf-lower "$CONF_LOWER" --tempo-sidecar-conf-upper "$CONF_UPPER")
    fi
    if [[ -n "$FAIL_ON_CLIP_DBFS" ]]; then
      CMD+=(--fail-on-clipping-dbfs "$FAIL_ON_CLIP_DBFS")
    fi
    "${CMD[@]}"
  else
    echo "[ERR] Missing tools/ma_audio_features.py" >&2
    exit 1
  fi

  # 2) Merge into stable schema (duration_sec, tempo_bpm, key, mode, loudness_LUFS, etc)
  if [[ -x "$REPO/tools/equilibrium_merge.py" ]]; then
    echo "[merge] tools/equilibrium_merge.py"
    "$PY_BIN" "$REPO/tools/equilibrium_merge.py" \
      --internal "$FEATURES_JSON" \
      --out "$MERGED_JSON"
  else
    echo "[ERR] Missing tools/equilibrium_merge.py" >&2
    exit 1
  fi

  # 3) Client helper only (NO PACK WRITING HERE)
  if [[ -x "$REPO/tools/pack_writer.py" ]]; then
  echo "[client] tools/pack_writer.py (--no-pack)"
  "$PY_BIN" "$REPO/tools/pack_writer.py" \
    --merged "$MERGED_JSON" \
    --out-dir "$OUT_DIR" \
    --anchor "00_core_modern" \
    --client-txt "$CLIENT_TXT" \
    --client-json "$CLIENT_JSON" \
    --no-pack
  else
    echo "[ERR] Missing tools/pack_writer.py" >&2
    exit 1
  fi

  echo "[OK] $stem → $OUT_DIR"
done

echo "[OK] Extraction complete."
