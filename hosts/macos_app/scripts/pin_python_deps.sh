#!/usr/bin/env zsh
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname "$0")/../.." && pwd)"
PY_BIN="/usr/local/bin/python3"

echo "Using repo root: $REPO_ROOT"
echo "Using python:    $PY_BIN"
echo "Installing pinned deps: numpy<2, scipy<1.12, librosa>=0.10,<0.11"

cd "$REPO_ROOT"
PYTHONPATH="$REPO_ROOT" "$PY_BIN" -m pip install "numpy<2" "scipy<1.12" "librosa>=0.10,<0.11"

echo "Done."
