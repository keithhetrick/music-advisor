#!/bin/zsh
set -euo pipefail

##############################################################################
# ma_hci_builder.sh
#
# Automator #2 backend:
#   - Takes one or more dragged files/folders (WIPs or benchmarks).
#   - Resolves the track directory containing:
#       * one or more *.features.json
#       * one *.client.json (or similar)
#   - For each track directory, computes:
#       [1] Audio axes + raw HCI_v1 (hci_axes.py)
#       [2] HCI_v1 calibration (hci_calibration.py apply)
#       [3] Final-score policy / caps (hci_final_score.py)
#       [4] PHILOSOPHY block into HCI  JSON (ma_add_philosophy_to_hci.py)
#       [5] Historical Echo v1 summary into HCI JSON (ma_add_echo_to_hci_v1.py)
#       [6] Merge client JSON + HCI into .client.rich.txt (ma_merge_client_and_hci.py)
#       [7] Compact PHILOSOPHY line into .client.rich.txt (ma_add_philosophy_to_client_rich.py)
#       [8] Historical Echo v1 (full) into .client.rich.txt (ma_add_echo_to_client_rich_v1.py)
#
# Notes:
#   - This script is designed to be called by Automator (via scripts/automator_wrapper.sh)
#     but also works directly from CLI.
#   - It is intentionally “boring and stable” for HCI_v1.
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

# Resolve repo root relative to this script
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
BIN_DIR="${BIN_DIR:-$REPO/.venv/bin}"

# Ensure repo root + src on PYTHONPATH so adapters/sitecustomize are available.
export PYTHONPATH="$REPO:$REPO/src:${PYTHONPATH:-}"
export PATH="$BIN_DIR:$PATH"

# Optional: tee stdout/stderr to a log file (set HCI_BUILDER_LOG to enable)
if [[ -n "${HCI_BUILDER_LOG:-}" ]]; then
  exec > >(tee -a "$HCI_BUILDER_LOG") 2>&1
  echo "[INFO] Logging to $HCI_BUILDER_LOG"
fi

# Enforce pinned deps to avoid runtime version drift (warn and exit if mismatched).
PIN_CHECK_PY="${PY:-}"
if [[ -z "$PIN_CHECK_PY" ]]; then
  if [[ -x "$REPO/.venv/bin/python" ]]; then
    PIN_CHECK_PY="$REPO/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PIN_CHECK_PY="$(command -v python3)"
  fi
fi
if [[ -n "$PIN_CHECK_PY" ]]; then
  if ! "$PIN_CHECK_PY" - <<'PY' 2>/dev/null; then
import importlib, sys
expected = {
    "numpy": "1.26.4",
    "scipy": "1.11.4",
    "librosa": "0.10.1",
}
bad = []
for mod, want in expected.items():
    try:
        have = importlib.import_module(mod).__version__
    except Exception:
        bad.append(f"{mod}: missing (want {want})")
        continue
    if have != want:
        bad.append(f"{mod}: {have} (want {want})")
if bad:
    raise SystemExit("Version drift detected: " + "; ".join(bad))
PY
    echo "[ERR] Python deps diverge from requirements.lock; run 'source .venv/bin/activate && pip install -r requirements.lock'." >&2
    exit 1
  fi
fi

# Prefer an already-active venv, then repo venv, then system python3
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  PY="python"
elif [[ -x "$REPO/.venv/bin/python" ]]; then
  PY="$REPO/.venv/bin/python"
else
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 not found; create/activate a venv in $REPO/.venv" >&2
    exit 1
  fi
  PY="python3"
fi

if [[ -x "$REPO/.venv/bin/python" && -z "${VIRTUAL_ENV:-}" ]]; then
  echo "[INFO] Using repo venv: $REPO/.venv (activate it for faster launches)" >&2
fi

# Shared calibration + norms (v1 pipeline)
CALIB_JSON="${AUDIO_HCI_CALIBRATION:-$REPO/shared/calibration/hci_calibration_us_pop_v1.json}"
MARKET_NORMS="${AUDIO_MARKET_NORMS:-$REPO/shared/calibration/market_norms_us_pop.json}"
CORE_CSV="$REPO/data/spine/spine_core_tracks_v1.csv"
# Prefer the in-repo script to avoid stale console_scripts in the venv.
MA_MERGE_CLIENT_HCI_CLI="${MA_MERGE_CLIENT_HCI_CLI:-$REPO/tools/ma_merge_client_and_hci.py}"
MA_ADD_PHILO_HCI_CLI="${MA_ADD_PHILO_HCI_CLI:-$REPO/tools/ma_add_philosophy_to_hci.py}"
MA_ADD_ECHO_HCI_CLI="${MA_ADD_ECHO_HCI_CLI:-$REPO/tools/ma_add_echo_to_hci_v1.py}"
MA_ADD_PHILO_CLIENT_CLI="${MA_ADD_PHILO_CLIENT_CLI:-$REPO/tools/ma_add_philosophy_to_client_rich.py}"
MA_ADD_ECHO_CLIENT_CLI="${MA_ADD_ECHO_CLIENT_CLI:-$REPO/tools/hci/ma_add_echo_to_client_rich_v1.py}"

# Fallbacks if console scripts are not installed in the venv
# (merge CLI already points to the in-repo script by default)
# (remaining fallbacks kept for safety)
if [[ ! -x "$MA_ADD_PHILO_HCI_CLI" ]]; then
  MA_ADD_PHILO_HCI_CLI="$REPO/tools/ma_add_philosophy_to_hci.py"
fi
if [[ ! -x "$MA_ADD_ECHO_HCI_CLI" ]]; then
  MA_ADD_ECHO_HCI_CLI="$REPO/tools/ma_add_echo_to_hci_v1.py"
fi
if [[ ! -x "$MA_ADD_PHILO_CLIENT_CLI" ]]; then
  MA_ADD_PHILO_CLIENT_CLI="$REPO/tools/ma_add_philosophy_to_client_rich.py"
fi
if [[ ! -x "$MA_ADD_ECHO_CLIENT_CLI" ]]; then
  MA_ADD_ECHO_CLIENT_CLI="$REPO/tools/hci/ma_add_echo_to_client_rich_v1.py"
fi

# Dynamic default YEAR_MAX: highest year in spine_core_tracks_v1.csv (override with env YEAR_MAX)
if [[ -z "${YEAR_MAX:-}" ]]; then
  if [[ -f "$CORE_CSV" ]]; then
    CORE_PATH="$CORE_CSV" YEAR_MAX="$("$PY" - <<'PY'
import csv, os, pathlib
p = pathlib.Path(os.environ.get("CORE_PATH", ""))
max_year = None
if p.is_file():
    try:
        with p.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                y = row.get("year") or ""
                try:
                    yi = int(y)
                except ValueError:
                    continue
                if max_year is None or yi > max_year:
                    max_year = yi
    except Exception:
        max_year = None
if max_year:
    print(max_year)
PY
)" || YEAR_MAX=""
  fi
  if [[ -z "$YEAR_MAX" ]]; then
    echo "[WARN] CORE_PATH missing or unreadable; defaulting YEAR_MAX=2020" >&2
    YEAR_MAX=2020
  else
    echo "[INFO] YEAR_MAX (auto) set to $YEAR_MAX from spine_core_tracks_v1.csv" >&2
  fi
fi

# Resolve ECHO_TIERS: user env wins; otherwise, auto-enable Tier 2 / Tier 3 if their tables exist.
if [[ -z "${ECHO_TIERS:-}" ]]; then
DB_PATH="${HISTORICAL_ECHO_DB:-${REPO}/data/historical_echo/historical_echo.db}"
  AUTO_TIERS="tier1_modern"
  if [[ -f "$DB_PATH" ]]; then
    HAS_TIER2="$(sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='spine_master_tier2_modern_lanes_v1';")" || HAS_TIER2=""
    HAS_TIER3="$(sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='spine_master_tier3_modern_lanes_v1';")" || HAS_TIER3=""
    if [[ -n "$HAS_TIER2" ]]; then
      AUTO_TIERS="${AUTO_TIERS},tier2_modern"
    fi
    if [[ -n "$HAS_TIER3" ]]; then
      AUTO_TIERS="${AUTO_TIERS},tier3_modern"
    fi
    if [[ "$AUTO_TIERS" != "tier1_modern" ]]; then
      ECHO_TIERS="$AUTO_TIERS"
      echo "[INFO] ECHO_TIERS auto-set to $ECHO_TIERS (detected Tier 2/3 tables)." >&2
    fi
  fi
fi
ECHO_TIERS="${ECHO_TIERS:-tier1_modern}"
# Optional flags
SKIP_CLIENT="${SKIP_CLIENT:-0}"   # 1 to skip client merge/echo steps
DRY_RUN="${DRY_RUN:-0}"     # 1 to print commands without executing

run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf "[DRY] "
    printf "%q " "$@"
    printf "\n"
  else
    "$@"
  fi
}

if [[ ! -f "$CALIB_JSON" ]]; then
  echo "[ERROR] Calibration JSON not found: $CALIB_JSON" >&2
  exit 1
fi

if [[ ! -f "$MARKET_NORMS" ]]; then
  echo "[ERROR] Market norms JSON not found: $MARKET_NORMS" >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  cat >&2 <<USAGE
Usage:
  $0 <track_dir_or_root> [<track_dir_or_root> ...]

Examples:
  $0 "features_output/2025/11/20/Bad Guy (Jo Tyler, Keith Hetrick 11.19.2025) - worktape"
  $0 "features_output/2025/11/20"

Environment:
  ECHO_TIERS=tier1_modern,tier2_modern,tier3_modern  # auto if Tier 2/3 tables exist; set to tier1_modern to force Tier 1 only
USAGE
  exit 1
fi

required_tools=(
  "$REPO/tools/hci_axes.py"
  "$REPO/tools/hci_calibration.py"
  "$REPO/tools/hci_final_score.py"
  "$REPO/tools/ma_add_philosophy_to_hci.py"
  "$REPO/tools/ma_add_echo_to_hci_v1.py"
  "$REPO/tools/ma_merge_client_and_hci.py"
  "$REPO/tools/append_metadata_to_client_rich.py"
  "$REPO/tools/ma_add_philosophy_to_client_rich.py"
  "$REPO/tools/hci/ma_add_echo_to_client_rich_v1.py"
)
for tool in "${required_tools[@]}"; do
  if [[ ! -f "$tool" ]]; then
    echo "[ERROR] Missing tool: $tool" >&2
    exit 1
  fi
done

##############################################################################
# Helper: find track directories under a root
#
# Behaviour:
#   - If root is a directory and has *.features.json directly:
#       → treat root itself as one track_dir.
#   - Additionally, for any direct subdirectory containing *.features.json:
#       → treat each subdirectory as a track_dir.
#   - If root is a file:
#       → use its parent directory as the track_dir.
#
# Output: one track_dir per line (absolute path), safe for spaces.
##############################################################################
find_track_dirs_for_root() {
  local root="$1"

  # Normalize to absolute path if possible
  if [[ -d "$root" ]]; then
    root="$(cd "$root" && pwd)"
  elif [[ -f "$root" ]]; then
    local parent="${root:h}"
    root="$(cd "$parent" && pwd)"
  fi

  if [[ -d "$root" ]]; then
    # Case 1: root itself is a track_dir (has *.features.json)
    if ls "$root"/*.features.json >/dev/null 2>&1; then
      echo "$root"
    fi

    # Case 2: any immediate subdirectories that look like track_dirs
    for d in "$root"/*; do
      if [[ -d "$d" ]] && ls "$d"/*.features.json >/dev/null 2>&1; then
        echo "$(cd "$d" && pwd)"
      fi
    done
  elif [[ -f "$root" ]]; then
    # Fallback: parent directory of a file
    local dir="${root:h}"
    echo "$(cd "$dir" && pwd)"
  fi
}

##############################################################################
# Main
##############################################################################

any_found=0

for input in "$@"; do
  # For each argument, find one or more track_dirs
  while IFS= read -r track_dir; do
    [[ -z "$track_dir" ]] && continue
    any_found=1

    # Basic sanity: need at least one *.features.json
    FEATURES_JSON="$(ls -t "$track_dir"/*.features.json 2>/dev/null | head -n 1 || true)"
    if [[ -z "$FEATURES_JSON" ]]; then
      echo "[WARN] No *.features.json found under: $track_dir — skipping." >&2
      continue
    fi

    stem="${track_dir:t}"
    echo "────────────────────────────────────────────────────────"
    echo "[INFO] Processing track_dir: $track_dir (stem=$stem)"

    HCI_JSON="$track_dir/$stem.hci.json"
    CLIENT_JSON="$track_dir/$stem.client.json"
    CLIENT_RICH="$track_dir/$stem.client.rich.txt"
    INPUT_JSON="$CLIENT_JSON"
    OUTPUT_RICH="$CLIENT_RICH"

    echo "[1/8] Axes + raw HCI_v1 → $HCI_JSON"
    run_cmd "$PY" "$REPO/tools/hci_axes.py" \
      --features "$FEATURES_JSON" \
      --market-norms "$MARKET_NORMS" \
      --out "$HCI_JSON"

    echo "[2/8] Apply HCI_v1 calibration → $HCI_JSON"
    run_cmd "$PY" "$REPO/tools/hci_calibration.py" apply \
      --root "$track_dir" \
      --calib "$CALIB_JSON"

    echo "[3/8] Apply final-score policy (WIP caps / benchmark tiers)"
    run_cmd "$PY" "$REPO/tools/hci_final_score.py" \
      --root "$track_dir" \
      --recompute

    echo "[4/8] Add PHILOSOPHY block into HCI JSON"
    run_cmd "$PY" "$MA_ADD_PHILO_HCI_CLI" \
      --root "$track_dir"

  echo "[5/8] Add Historical Echo v1 summary into HCI JSON"
  run_cmd "$PY" "$MA_ADD_ECHO_HCI_CLI" \
    --root "$track_dir" \
    --db "$DB_PATH" \
    --year-max "$YEAR_MAX" \
    --tiers "$ECHO_TIERS"

  if [[ "$SKIP_CLIENT" == "1" ]]; then
    echo "[INFO] SKIP_CLIENT=1 — skipping client merge + echo injection."
    elif [[ -n "$INPUT_JSON" ]]; then
      echo "[6/8] Merge client JSON + HCI → $OUTPUT_RICH"
      run_cmd "$PY" "$MA_MERGE_CLIENT_HCI_CLI" \
        --client-json "$INPUT_JSON" \
        --hci      "$HCI_JSON" \
        --client-out "$OUTPUT_RICH"

      echo "[7/8] Inject compact PHILOSOPHY line into rich txt"
      run_cmd "$PY" "$MA_ADD_PHILO_CLIENT_CLI" \
        --root "$track_dir"

      echo "[8/8] Inject historical echo into rich txt"
      run_cmd "$PY" "$MA_ADD_ECHO_CLIENT_CLI" \
        --root "$track_dir" \
        --db "$DB_PATH" \
        --year-max "$YEAR_MAX" \
        --tiers "$ECHO_TIERS"

      echo "[9/8] Append audio metadata probe into rich txt (best-effort)"
      run_cmd "$PY" "$REPO/tools/append_metadata_to_client_rich.py" \
        --track-dir "$track_dir" || true
    else
      echo "[WARN] No client JSON found for $track_dir; skipping rich TXT merge + PHILOSOPHY/ECHO injection." >&2
    fi

    echo "[OK] Done: $stem"
done < <(find_track_dirs_for_root "$input")
done

if [[ "$any_found" -eq 0 ]]; then
  echo "[WARN] No track directories found from provided inputs."
  exit 0
fi

echo "[OK] HCI builder complete."


##############################################################################
# FUTURE SWITCH TO v2 (commented out – keep for later)
#
# When v2 is ready, instead of calling hci_axes.py + hci_calibration.py,
# you can replace the [1/4] + [3/4] blocks above with something like:
#
#   echo "[1/2] Computing audio_axes + HCI_v1_score + HCI_audio_v2 via ma_simple_hci_from_features"
#   "$PY" -m tools.ma_simple_hci_from_features \
#     --features "$FEATURES_JSON" \
#     --out "$HCI_JSON"
#
#   echo "[2/2] Building rich client payload → $CLIENT_RICH"
#   "$PY" "$REPO/tools/ma_merge_client_and_hci.py" \
#     --client-json "$CLIENT_JSON" \
#     --hci      "$HCI_JSON" \
#     --out      "$CLIENT_RICH"
#
# For now we keep the v1 flow stable.
##############################################################################
