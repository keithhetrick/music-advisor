#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

python_cmd="${PYTHON:-${repo_root}/.venv/bin/python3}"

exec "${python_cmd}" tools/lyric_wip_pipeline.py "$@"
