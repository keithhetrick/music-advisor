#!/usr/bin/env zsh
set -euo pipefail

REPO_ROOT="${MA_APP_DEFAULT_WORKDIR:-/Users/keithhetrick/music-advisor}"
PY_BIN="${MA_APP_DEFAULT_CMD:-/usr/local/bin/python3}"
SCRIPT="${MA_APP_DEFAULT_SCRIPT:-$REPO_ROOT/engines/audio_engine/tools/cli/ma_audio_features.py}"
AUDIO="${MA_APP_DEFAULT_AUDIO:-/Users/keithhetrick/Downloads/lola.mp3}"
OUT="${MA_APP_DEFAULT_OUT:-/tmp/ma_features.json}"
PY_PATH="${MA_APP_ENV_PYTHONPATH:-$REPO_ROOT}"

echo "repo:   $REPO_ROOT"
echo "python: $PY_BIN"
echo "script: $SCRIPT"
echo "audio:  $AUDIO"
echo "out:    $OUT"

cd "$REPO_ROOT"
PYTHONPATH="$PY_PATH" "$PY_BIN" "$SCRIPT" --audio "$AUDIO" --out "$OUT"

if [ ! -s "$OUT" ]; then
  echo "FAIL: sidecar not written: $OUT"
  exit 1
fi

echo "OK: sidecar written to $OUT"
