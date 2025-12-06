#!/usr/bin/env zsh
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"
cmake -S "$SCRIPT_DIR" -B "$SCRIPT_DIR/build" -G Xcode
cmake --build "$SCRIPT_DIR/build" --config Debug
