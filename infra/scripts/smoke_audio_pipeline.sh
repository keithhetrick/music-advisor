#!/usr/bin/env bash

# Quick smoke test for the audio pipeline + sidecar.
# - Assumes the repo venv is already set up.
# - Requires an audio file path as $1.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 /path/to/audio" >&2
  exit 2
fi

AUDIO="$1"
if [[ ! -f "$AUDIO" ]]; then
  echo "[smoke] audio not found: $AUDIO" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENVDIR="$REPO_ROOT/.venv"

if [[ ! -d "$VENVDIR" ]]; then
  echo "[smoke] venv missing at $VENVDIR" >&2
  exit 1
fi

PY="$VENVDIR/bin/python"
export PATH="$VENVDIR/bin:$PATH"
if [[ ! -x "$PY" ]]; then
  echo "[smoke] python not executable at $PY" >&2
  exit 1
fi

TMPDIR="$(mktemp -d /tmp/ma_smoke.XXXXXX)"
require_safe_subpath "/tmp" "$TMPDIR" || { echo "[smoke] tmpdir outside /tmp"; exit 64; }
OUT="$TMPDIR/out.features.json"
SIDECAR="$TMPDIR/out.sidecar.json"
cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT
export LOG_REDACT="${LOG_REDACT:-1}"
export LOG_SANDBOX="${LOG_SANDBOX:-1}"
export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src:${PYTHONPATH:-}"
# Force sidecar to use venv python so deps (jsonschema/etc.) are available.
export MA_SIDECAR_CMD="$PY $REPO_ROOT/tools/tempo_sidecar_runner.py --audio {audio} --out {out}"
export ALLOW_CUSTOM_SIDECAR_CMD=1
export SIDECAR_TIMEOUT_SECONDS="${SIDECAR_TIMEOUT_SECONDS:-30}"

echo "[smoke] running sidecar-backed pipeline..."
set +e
"$PY" "$REPO_ROOT/tools/ma_audio_features.py" \
  --audio "$AUDIO" \
  --out "$OUT" \
  --tempo-backend sidecar \
  --tempo-sidecar-json-out "$SIDECAR" \
  --tempo-sidecar-cmd "$MA_SIDECAR_CMD" \
  --force
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  echo "[smoke] FAIL (status $STATUS)"
  exit $STATUS
fi

if [[ ! -s "$OUT" ]]; then
  echo "[smoke] FAIL (no features output)"
  exit 1
fi

echo "[smoke] PASS"
echo "[smoke] features: $OUT"
echo "[smoke] sidecar : $SIDECAR"
