#!/bin/zsh
set -euo pipefail

# CI-friendly smoke: generate a short tone and run the full chain smoke.
# Usage: scripts/ci_smoke.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
export PYTHONPATH="$REPO:$REPO/src:${PYTHONPATH:-}"

PY="$REPO/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "[ERR] python3 not found; create/activate $REPO/.venv" >&2
    exit 1
  fi
fi

TMP_DIR="$(mktemp -d)"
TONE="$TMP_DIR/ci_smoke_tone.wav"
require_safe_subpath "$TMP_DIR" "$TMP_DIR" || { echo "[ci-smoke] tmp dir outside allowed root"; exit 64; }

echo "[ci-smoke] using PY=$PY"
echo "[ci-smoke] generating tone -> $TONE"

"$PY" - <<'PY' "$TONE"
import math, wave, struct, sys
if len(sys.argv) < 2:
    raise SystemExit("missing output path")
out = sys.argv[1]
sr = 44100
dur = 1.0
f = 440.0
n = int(sr * dur)
w = wave.open(out, "w")
w.setnchannels(1)
w.setsampwidth(2)
w.setframerate(sr)
for i in range(n):
    val = int(0.2 * 32767 * math.sin(2 * math.pi * f * i / sr))
    w.writeframes(struct.pack("<h", val))
w.close()
PY

zsh "$REPO/scripts/smoke_full_chain.sh" "$TONE"

# Lint: enforce strict summary and stage logs presence
OUT_DIR=$(ls -td "$REPO"/features_output/smoke/* 2>/dev/null | head -n1)
if [[ -z "$OUT_DIR" ]]; then
  echo "[ci-smoke] ERROR: no smoke output found" >&2
  exit 1
fi
echo "[ci-smoke] validating logs under $OUT_DIR"
LOG_JSON=0 "$REPO/.venv/bin/python" "$REPO/tools/log_summary.py" --out-dir "$OUT_DIR" --strict

echo "[ci-smoke] complete; artifacts under features_output/smoke"
