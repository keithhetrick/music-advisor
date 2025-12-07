#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

./smoke_default.sh
