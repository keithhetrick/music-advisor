#!/bin/bash
# scripts/run_full_pipeline.sh — validator (orig+bypass) + engine + notifications
# macOS bash 3.2 compatible
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$PROJECT_ROOT/config/pipeline.env"
if [ -f "$CONFIG" ]; then
  # shellcheck source=/dev/null
  . "$CONFIG"
fi

OUTPUT_ROOT_VAL="${OUTPUT_ROOT:-$PROJECT_ROOT/features_output}"
ENGINE_ROOT_VAL="${ENGINE_ROOT:-$PROJECT_ROOT/vendor/MusicAdvisor}"
ENGINE_PY_VAL="${ENGINE_PY:-$PROJECT_ROOT/.venv/bin/python}"
AUDIOTOOLS_PY_VAL="${AUDIOTOOLS_PY:-$PROJECT_ROOT/.venv/bin/python}"
PACKAGE_NAME_VAL="${PACKAGE_NAME:-MusicAdvisor}"
NOTIFY_VAL="${NOTIFY:-1}"

LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
RUN_LOG="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

log() { echo "$@" | tee -a "$RUN_LOG" >/dev/null; }
notify() {
  [ "$NOTIFY_VAL" = "1" ] || return 0
  /usr/bin/osascript <<OSA >/dev/null 2>&1 || true
display notification "$(echo "$3" | sed 's/"/\\"/g')" with title "$(echo "$1" | sed 's/"/\\"/g')" subtitle "$(echo "$2" | sed 's/"/\\"/g')"
OSA
}

# --- args ---
if [ "${1:-}" = "--from-output" ]; then
  TARGET_DIR="${2:-}"
  [ -d "$TARGET_DIR" ] || { echo "ERROR: Not a directory: $TARGET_DIR"; exit 64; }
else
  echo "Usage: $0 --from-output <analysis_dir>"; exit 64
fi

# --- preflight ---
log "[log] writing to $RUN_LOG"
log "=== Preflight ==="
log "PROJECT_ROOT:   $PROJECT_ROOT"
log "CONFIG:         $CONFIG"
log "OUTPUT_ROOT:    $OUTPUT_ROOT_VAL"
log "ENGINE_ROOT:    $ENGINE_ROOT_VAL"
log "AUDIOTOOLS_PY:  $AUDIOTOOLS_PY_VAL"
log "ENGINE_PY:      $ENGINE_PY_VAL"
log "NOTIFY:         $NOTIFY_VAL"

# Pick newest pack/client in the folder
PACK="$(ls -t "$TARGET_DIR"/*.pack.json 2>/dev/null | head -n1 || true)"
CLIENT="$(ls -t "$TARGET_DIR"/*client*.txt 2>/dev/null | head -n1 || true)"
log "$(date +%F\ %T) === PROCESSING OUTPUT DIR: $TARGET_DIR ==="
log "PACK=$PACK"
log "CLIENT=$CLIENT"
log "BUILDER_EXPORT=<none>"

if [ -z "$PACK" ] || [ ! -f "$PACK" ]; then
  log "ERROR: no .pack.json found in $TARGET_DIR"
  exit 66
fi
if [ -z "$CLIENT" ] || [ ! -f "$CLIENT" ]; then
  log "WARN: no client rich txt found; continuing but policy may be minimal"
fi

# --- VALIDATOR (ORIGINAL) ---
log ""
log "=== VALIDATOR (ORIGINAL) ==="
ORIG_JSON="/tmp/validator_original.json"
set +e
"$AUDIOTOOLS_PY_VAL" "$PROJECT_ROOT/tools/validator/verbose_validator.py" "$PACK" "${CLIENT:-/dev/null}" > "$ORIG_JSON" 2>>"$RUN_LOG"
set -e
log "Wrote $ORIG_JSON"

# --- VALIDATOR (BYPASS) ---
log ""
log "=== VALIDATOR (BYPASS) ==="
BYPASS_CLIENT="/tmp/$(basename "${CLIENT:-pack}").bypass.txt"
if [ -n "${CLIENT:-}" ] && [ -f "$CLIENT" ]; then
  # flip the two toggles in a safe way
  sed 's/use_ttc=false/use_ttc=true/g; s/use_exposures=false/use_exposures=true/g' "$CLIENT" > "$BYPASS_CLIENT"
else
  echo "# (stub) BYPASS policy when client rich missing" > "$BYPASS_CLIENT"
fi
BYPASS_JSON="/tmp/validator_bypass.json"
set +e
"$AUDIOTOOLS_PY_VAL" "$PROJECT_ROOT/tools/validator/verbose_validator.py" "$PACK" "$BYPASS_CLIENT" > "$BYPASS_JSON" 2>>"$RUN_LOG"
set -e
log "Wrote $BYPASS_JSON"

# --- ENGINE (LOCAL) ---
log ""
log "=== ENGINE (LOCAL) ==="
log "ENGINE_PY: $ENGINE_PY_VAL"
echo "python: $ENGINE_PY_VAL" | tee -a "$RUN_LOG"

# Discover advisor_cli.py and package dir
CLI_PATH="$(find "$ENGINE_ROOT_VAL" -type f -name 'advisor_cli.py' -path '*/CLI/*' -print -quit 2>/dev/null || true)"
PKG_DIR_CANDIDATE=""
if [ -n "$CLI_PATH" ]; then
  PKG_DIR_CANDIDATE="$(dirname "$(dirname "$CLI_PATH")")"   # .../<pkg>/CLI/advisor_cli.py -> .../<pkg>
  [ -f "$PKG_DIR_CANDIDATE/__init__.py" ] || { : > "$PKG_DIR_CANDIDATE/__init__.py"; log "[Engine] created __init__.py in $PKG_DIR_CANDIDATE"; }
  [ -d "$PKG_DIR_CANDIDATE/CLI" ]  && { [ -f "$PKG_DIR_CANDIDATE/CLI/__init__.py" ]  || { : > "$PKG_DIR_CANDIDATE/CLI/__init__.py";  log "[Engine] created CLI/__init__.py"; }; }
  [ -d "$PKG_DIR_CANDIDATE/Core" ] && { [ -f "$PKG_DIR_CANDIDATE/Core/__init__.py" ] || { : > "$PKG_DIR_CANDIDATE/Core/__init__.py"; log "[Engine] created Core/__init__.py"; }; }
fi

# Build PYTHONPATH (repo root + package dir)
if [ -n "$PKG_DIR_CANDIDATE" ]; then
  export PYTHONPATH="$ENGINE_ROOT_VAL:$PKG_DIR_CANDIDATE"
else
  export PYTHONPATH="$ENGINE_ROOT_VAL"
fi
log "[Engine] Using PYTHONPATH: $PYTHONPATH"
log "[Engine] PACKAGE_NAME: $PACKAGE_NAME_VAL"
[ -n "$PKG_DIR_CANDIDATE" ] && log "[Engine] PKG_DIR_CANDIDATE: $PKG_DIR_CANDIDATE"
[ -n "$CLI_PATH" ] && log "[Engine] CLI_PATH: $CLI_PATH"
log "[Engine] ls ENGINE_ROOT:"
ls -la "$ENGINE_ROOT_VAL" | sed 's/^/[ls] /' | tee -a "$RUN_LOG" >/dev/null
if [ -n "$PKG_DIR_CANDIDATE" ]; then
  log "[Engine] ls PKG_DIR_CANDIDATE:"
  ls -la "$PKG_DIR_CANDIDATE" | sed 's/^/[ls] /' | tee -a "$RUN_LOG" >/dev/null
fi

LOCAL_EXPORT="/tmp/$(basename "$PACK").local_export.json"
ENGINE_STDOUT="/tmp/engine_stdout_$(date +%s).txt"
ENGINE_STDERR="/tmp/engine_stderr_$(date +%s).txt"

# 1) Try modular import
set +e
"$ENGINE_PY_VAL" -m "$PACKAGE_NAME_VAL.CLI.advisor_cli" \
  --pack "$PACK" \
  --client  "${CLIENT:-$BYPASS_CLIENT}" \
  --export "$LOCAL_EXPORT" \
  --print-audit >"$ENGINE_STDOUT" 2>"$ENGINE_STDERR"
engine_rc=$?
set -e

# 2) Fallback to direct path if module import failed
if [ $engine_rc -ne 0 ] && [ -n "$CLI_PATH" ]; then
  log "[WARN] Module import failed; falling back to CLI path"
  set +e
  "$ENGINE_PY_VAL" "$CLI_PATH" \
    --pack "$PACK" \
    --client  "${CLIENT:-$BYPASS_CLIENT}" \
    --export "$LOCAL_EXPORT" \
    --print-audit >"$ENGINE_STDOUT" 2>"$ENGINE_STDERR"
  engine_rc=$?
  set -e
fi

# 3) If still failing, show errors and exit
if [ $engine_rc -ne 0 ]; then
  log "[ERROR] Engine CLI failed (rc=$engine_rc)."
  log "--- ENGINE STDOUT (last 80 lines) ---"
  tail -n 80 "$ENGINE_STDOUT" | sed 's/^/[engine:stdout] /' | tee -a "$RUN_LOG"
  log "--- ENGINE STDERR (last 80 lines) ---"
  tail -n 80 "$ENGINE_STDERR" | sed 's/^/[engine:stderr] /' | tee -a "$RUN_LOG"
  notify "Pipeline failed" "$(basename "$TARGET_DIR")" "Engine CLI error (see log)"
  exit $engine_rc
fi

# Success: show a snippet of output
log "--- ENGINE OUTPUT (first 80 lines) ---"
head -n 80 "$ENGINE_STDOUT" | sed 's/^/[engine] /' | tee -a "$RUN_LOG"

# --- Extract HCI for the finish notification (best-effort) ---
HCI_JSON="/tmp/hci_$(date +%s).json"
python_json_grab=$(
  /usr/bin/python3 - "$ENGINE_STDOUT" <<'PY' 2>/dev/null || true
import sys, json, re, pathlib
p = pathlib.Path(sys.argv[1]).read_text(errors="ignore")
m = re.search(r'\{.*\}', p, re.S)
if not m:
    sys.exit(1)
try:
    obj = json.loads(m.group(0))
except Exception:
    sys.exit(2)
print(json.dumps(obj))
PY
)
if [ -n "$python_json_grab" ]; then
  echo "$python_json_grab" > "$HCI_JSON"
  OUT_JSON="$TARGET_DIR/engine_audit.json"
  cp "$HCI_JSON" "$OUT_JSON" 2>/dev/null || true
  log "Saved engine JSON -> $OUT_JSON"

  HCI=$(/usr/bin/python3 - <<'PY' "$HCI_JSON" 2>/dev/null || true
import sys, json, pathlib
j = json.loads(pathlib.Path(sys.argv[1]).read_text())
h = j.get("HCI_v1",{})
print(f'{h.get("HCI_v1_score","-")}|{h.get("Market","-")}|{h.get("Emotional","-")}')
PY
)
  HCI_SCORE=$(echo "$HCI" | cut -d'|' -f1)
  HCI_MARKET=$(echo "$HCI" | cut -d'|' -f2)
  HCI_EMO=$(echo "$HCI" | cut -d'|' -f3)
  if [ -n "$HCI_SCORE" ] && [ "$HCI_SCORE" != "-" ]; then
    notify "Pipeline finished" "$(basename "$TARGET_DIR")" "HCI ${HCI_SCORE} | Market ${HCI_MARKET} | Emotional ${HCI_EMO}"
  else
    notify "Pipeline finished" "$(basename "$TARGET_DIR")" "OK"
  fi
else
  notify "Pipeline finished" "$(basename "$TARGET_DIR")" "OK (no JSON parsed)"
fi

log "$(date +%F\ %T) === DONE: $TARGET_DIR ==="
