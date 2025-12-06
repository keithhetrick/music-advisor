#!/bin/zsh
set -euo pipefail

# Wrapper to run Python commands with repo env (PYTHONPATH + preferred venv).
# Usage: scripts/with_repo_env.sh python_args...

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
# Make repo modules discoverable (hosts + engines remain editable/uninstalled)
export PYTHONPATH="$REPO:$REPO/src:$REPO/hosts:$REPO/engines:$REPO/engines/recommendation_engine:$REPO/engines/audio_engine/src:$REPO/engines/lyrics_engine/src:$REPO/engines/ttc_engine/src:$REPO/hosts/advisor_host_core/src:${PYTHONPATH:-}"
export PATH="$REPO/.venv/bin:$PATH"

PY_BIN="${PY_BIN:-$REPO/.venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY_BIN="$(command -v python3)"
  else
    echo "[ERR] python3 not found; create/activate $REPO/.venv" >&2
    exit 1
  fi
fi

exec "$PY_BIN" "$@"
