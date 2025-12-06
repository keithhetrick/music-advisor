#!/usr/bin/env bash
#
# Lightweight smoke test for ranker + injectors using adapters/registries.
# Requires a folder with at least one .features.json that has already been
# processed (or can be processed) into .hci.json / .client.rich.txt files.
#
# Usage:
#   SMOKE_ROOT="/path/to/features_output/2025/11/26/Some Track" \
#   ./scripts/smoke_rank_inject.sh
#
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

ROOT="${SMOKE_ROOT:-}"
REPO="${REPO:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
PY_BIN="${PY_BIN:-$REPO/.venv/bin/python}"

if [[ -z "$ROOT" ]]; then
  echo "[smoke] Set SMOKE_ROOT to a folder containing .features.json/.hci.json/.client.rich.txt"
  exit 0
fi

if [[ ! -d "$ROOT" ]]; then
  echo "[smoke] SMOKE_ROOT does not exist: $ROOT"
  exit 1
fi
require_safe_subpath "$REPO/features_output" "$ROOT" || { echo "[smoke] ROOT outside features_output"; exit 64; }

if [[ ! -x "$PY_BIN" ]]; then
  echo "[smoke] Missing venv python at $PY_BIN"
  exit 1
fi

echo "[smoke] Running injectors with tempo confidence + neighbors split"
"$PY_BIN" "$REPO/tools/hci/ma_add_echo_to_client_rich_v1.py" --root "$ROOT" --use-tempo-confidence || exit 1
"$PY_BIN" "$REPO/tools/ma_add_echo_to_hci_v1.py" --root "$ROOT" --use-tempo-confidence || exit 1

echo "[smoke] Ranking folder (summarize QA)"
"$PY_BIN" "$REPO/tools/hci/hci_rank_from_folder.py" --root "$ROOT" --summarize-qa || exit 1

echo "[smoke] OK"
