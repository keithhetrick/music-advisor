#!/usr/bin/env sh
# Thin shim to canonical smoke runner.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="${SCRIPT_DIR%/tools}"

exec "$REPO/infra/scripts/smoke_full_chain.sh" "$@"
