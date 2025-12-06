#!/usr/bin/env bash
# Show policy-bypass status and (optionally) simulate subdomain/HCI deltas.
# Usage:
#   scripts/simulate_bypass.sh path/to/baseline_hci.json path/to/pack.json
# or:
#   scripts/simulate_bypass.sh path/to/pack.json

set -euo pipefail

if [[ "$#" -eq 2 ]]; then
  BASE="$1"; PACK="$2"
  [[ -f "$BASE" ]] || { echo "ERROR: baseline not found: $BASE" >&2; exit 4; }
  [[ -f "$PACK" ]] || { echo "ERROR: pack not found: $PACK" >&2; exit 5; }
  python3 tools/simulator/bypass_simulator.py "$BASE" "$PACK"
elif [[ "$#" -eq 1 ]]; then
  PACK="$1"
  [[ -f "$PACK" ]] || { echo "ERROR: pack not found: $PACK" >&2; exit 6; }
  python3 tools/simulator/bypass_simulator.py "$PACK"
else
  echo "Usage:" >&2
  echo "  scripts/simulate_bypass.sh baseline_hci.json pack.json" >&2
  echo "  scripts/simulate_bypass.sh pack.json" >&2
  exit 1
fi
