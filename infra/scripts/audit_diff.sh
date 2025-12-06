#!/usr/bin/env bash
# Pretty-diff two verbose audits (JSON on stdin or files).
# Usage:
#   scripts/audit_diff.sh <original.json> <bypass.json>
# or:
#   <cmd producing audit A> | scripts/audit_diff.sh - <(cmd producing audit B)
#
# Shows delta for fields.status and policy_snapshot toggles.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

A="${1:-}"
B="${2:-}"

if [[ -z "$A" || -z "$B" ]]; then
  echo "Usage: scripts/audit_diff.sh <original.json> <bypass.json>" >&2
  exit 1
fi

jq --version >/dev/null 2>&1 || { echo "ERROR: jq required." >&2; exit 2; }

if [[ "$A" == "-" ]]; then
  AJ="$(cat)"
else
  AJ="$(cat "$A")"
fi

if [[ "$B" == "-" ]]; then
  BJ="$(cat)"
else
  BJ="$(cat "$B")"
fi

# Extract a concise comparison map
oa=$(jq -r '
  {
    policy_snapshot: .policy_snapshot,
    fields_status: (.fields | to_entries | map({key, status: .value.status}) )
  }
' <<<"$AJ")

ob=$(jq -r '
  {
    policy_snapshot: .policy_snapshot,
    fields_status: (.fields | to_entries | map({key, status: .value.status}) )
  }
' <<<"$BJ")

echo "=== POLICY SNAPSHOT (ORIGINAL) ==="
echo "$oa" | jq '.policy_snapshot'
echo
echo "=== POLICY SNAPSHOT (BYPASS) ==="
echo "$ob" | jq '.policy_snapshot'
echo
echo "=== FIELD STATUS CHANGES (original → bypass) ==="
jq -n --argjson OA "$oa" --argjson OB "$ob" '
  def to_map(xs): xs | map({(.key): .status}) | add;
  {orig: (to_map($OA.fields_status)), byp: (to_map($OB.fields_status))} |
  .orig as $o | .byp as $b |
  ($o | keys_unsorted + $b | keys_unsorted | unique) as $keys |
  [ $keys[] | {field: ., orig: $o[.] // "N/A", byp: $b[.] // "N/A"} ]
' | jq -r '.[] | "\(.field)\t\(.orig) → \(.byp)"'
