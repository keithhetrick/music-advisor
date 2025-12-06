#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/run_rank_with_guardrails.sh --root features_output/2025/11/26 [extra args...]
# Defaults:
#   - unknown QA treated as warn/include
#   - tempo-confidence scoring can be enabled via extra args if desired
#   - QA penalty applied at 0.1 (adjust via --qa-penalty)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

ROOT=""
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      ROOT="$2"
      shift 2
      ;;
    *)
      EXTRA+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$ROOT" ]]; then
  echo "Usage: $0 --root <features_root> [extra hci_rank_from_folder args]" >&2
  exit 1
fi
require_safe_subpath "$(cd "$SCRIPT_DIR/.." && pwd)/features_output" "$ROOT" || { echo "Root outside features_output"; exit 64; }

python3 tools/hci_rank_from_folder.py \
  --root "$ROOT" \
  --unknown-qa warn \
  --qa-penalty 0.1 \
  --summarize-qa \
  --require-sidecar-backend essentia_madmom \
  --require-neighbors-file \
  "${EXTRA[@]}"
