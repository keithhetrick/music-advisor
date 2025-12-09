#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$(cd "$APP_DIR/../.." && pwd)"

echo "== Building macOS app (Debug) =="
HOME="$APP_DIR/build/home" SWIFTPM_DISABLE_SANDBOX=1 swift build \
  --package-path "$APP_DIR" \
  --scratch-path "$APP_DIR/build/.swiftpm" \
  --disable-sandbox

echo "== Chat engine smoke =="
PYTHONPATH="$ROOT" "$ROOT/engines/chat_engine/chat_engine.py" --help >/dev/null 2>&1 || true
PYTHONPATH="$ROOT" python "$ROOT/engines/chat_engine/cli_smoke.py" "$@"

echo "Done."
