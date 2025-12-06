#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

# Usage:
#   infra/scripts/run_echo_inject_guardrails.sh --root data/features_output/2025/11/26/Some Track [--dry-run]
# This runs both injectors with tempo-confidence weighting enabled by default.

ROOT=""
DRY=""
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      ROOT="$2"
      shift 2
      ;;
    --dry-run)
      DRY="--dry-run"
      shift
      ;;
    *)
      EXTRA+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$ROOT" ]]; then
  echo "Usage: $0 --root <features_root> [--dry-run] [extra injector args]" >&2
  exit 1
fi
require_safe_subpath "$SCRIPT_DIR/features_output" "$ROOT" || { echo "Root outside features_output"; exit 64; }

python3 tools/ma_add_echo_to_hci_v1.py \
  --root "$ROOT" \
  --use-tempo-confidence \
  --tempo-confidence-threshold 0.4 \
  --tempo-weight-low 0.3 \
  $DRY \
  "${EXTRA[@]}"

python3 tools/hci/ma_add_echo_to_client_rich_v1.py \
  --root "$ROOT" \
  --use-tempo-confidence \
  --tempo-confidence-threshold 0.4 \
  --tempo-weight-low 0.3 \
  $DRY \
  "${EXTRA[@]}"
