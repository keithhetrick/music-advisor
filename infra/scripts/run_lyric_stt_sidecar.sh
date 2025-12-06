#!/usr/bin/env bash
# Wrapper to run the lyric STT sidecar with a local cache and history expansion disabled.
set -euo pipefail
# Disable history expansion that breaks paths containing '!' characters.
set +H
if [ -n "${ZSH_VERSION-}" ]; then
  setopt NO_BANG_HIST
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

# Default cache locations (override by setting env vars before calling).
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${repo_root}/.cache}"
export WHISPER_CACHE_DIR="${WHISPER_CACHE_DIR:-${XDG_CACHE_HOME}/whisper}"

LYRIC_STT_WHISPER_MODEL="${LYRIC_STT_WHISPER_MODEL:-medium}"
export LYRIC_STT_WHISPER_MODEL
export LYRIC_LCI_PROFILE="${LYRIC_LCI_PROFILE:-lci_us_pop_v1}"
export LYRIC_LCI_CALIBRATION="${LYRIC_LCI_CALIBRATION:-shared/calibration/lci_calibration_us_pop_v1.json}"

python_cmd="${PYTHON:-${repo_root}/.venv/bin/python3}"

exec "${python_cmd}" tools/lyric_stt_sidecar.py process-wip "$@"
