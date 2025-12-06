#!/usr/bin/env bash
# ma_wip_to_client.sh
# One-command WIP → features → client payload (delegates to automator).

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ma_wip_to_client.sh /path/to/audio.wav" >&2
  exit 1
fi

AUDIO="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOMATOR="$SCRIPT_DIR/automator.sh"

if [[ ! -x "$AUTOMATOR" ]]; then
  echo "[ERR] automator.sh not found/executable at $AUTOMATOR" >&2
  exit 1
fi

"$AUTOMATOR" "$AUDIO"
