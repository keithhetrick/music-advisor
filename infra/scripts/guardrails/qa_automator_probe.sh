#!/bin/bash
set -euo pipefail
. "$(cd "$(dirname "$0")/../.." && pwd)/infra/scripts/lib_security.sh"
LOG="/tmp/qa_automator_probe_$(date +%Y%m%d_%H%M%S).log"
{
  echo "=== QA PROBE ==="
  echo "whoami: $(whoami)"
  echo "pwd: $(pwd)"
  echo "shell: $SHELL"
  echo "args: $#"
  i=0; for a in "$@"; do i=$((i+1)); echo "  [$i] $a"; done
} > "$LOG" 2>&1
/usr/bin/osascript -e 'display notification "Args='"$#"'" with title "Automator Probe" subtitle "'"$LOG"'"'
echo "$LOG"
