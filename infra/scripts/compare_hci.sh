#!/usr/bin/env bash
# compare_hci.sh — convenience wrapper for json_hci_diff.py
# Usage:
#   scripts/compare_hci.sh path/to/builder_export.json path/to/local_export.json
# Exit codes:
#   0 → match, 1 → different, 2 → error

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

L="${1:-}"; R="${2:-}"
if [[ -z "$L" || -z "$R" ]]; then
  echo "Usage: scripts/compare_hci.sh <builder_export.json> <local_export.json>" >&2
  exit 2
fi
[[ -f "$L" ]] || { echo "ERROR: file not found: $L" >&2; exit 2; }
[[ -f "$R" ]] || { echo "ERROR: file not found: $R" >&2; exit 2; }

# ensure the python tool exists
if [[ ! -f tools/compare/json_hci_diff.py ]]; then
  echo "ERROR: tools/compare/json_hci_diff.py not found." >&2
  exit 2
fi

python3 tools/compare/json_hci_diff.py "$L" "$R"
