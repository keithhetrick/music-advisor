#!/usr/bin/env zsh
set -euo pipefail

LOG_PATH="/tmp/macos_app_cmd.log"

if [ -f "$LOG_PATH" ]; then
  rm -f "$LOG_PATH"
  echo "Removed $LOG_PATH"
else
  echo "No log at $LOG_PATH"
fi
