#!/usr/bin/env zsh
# Minimal smoke runner that uses tools/pipeline_api.py via pipeline_runner.py.
# Keeps concerns separated from Automator scripts; useful for quick local checks.

set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd -P)"
. "$SCRIPT_DIR/lib_security.sh"

REPO_ROOT="$(cd -- "$(dirname "$0")/../.." && pwd -P)"
PYTHON="${REPO_ROOT}/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "[pipeline_smoke] missing venv python at $PYTHON" >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/audio.wav [--strict]" >&2
  exit 2
fi

AUDIO="$1"; shift || true
# Resolve features_output under data/ for new layout
OUT_DIR="${REPO_ROOT}/data/features_output/pipeline_smoke/$(date -u +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"
require_safe_subpath "$REPO_ROOT/data/features_output" "$OUT_DIR" || { echo "[pipeline_smoke] OUT_DIR outside data/features_output"; exit 64; }

echo "[pipeline_smoke] audio=$AUDIO out_dir=$OUT_DIR"
exec "$PYTHON" "${REPO_ROOT}/tools/pipeline_runner.py" --audio "$AUDIO" --out-dir "$OUT_DIR" "$@"
