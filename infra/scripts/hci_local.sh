#!/bin/bash
# scripts/hci_local.sh — minimal local HCI runner (macOS bash 3.2)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

# --- config you likely already have ---
REPO="${REPO:-$HOME/music-advisor}"
AUDIO_TOOLS="$REPO"
PY="$AUDIO_TOOLS/.venv/bin/python"

# Point to your engine code (either vendor copy or Desktop repo)
# Prefer vendor path (no permissions drama). If you keep a live repo on Desktop, you can set ENGINE_ROOT to that instead.
ENGINE_ROOT="${ENGINE_ROOT:-$REPO/vendor/MusicAdvisor}"
PACKAGE_NAME="${PACKAGE_NAME:-MusicAdvisor}"
require_safe_subpath "$HOME" "$ENGINE_ROOT" || { echo "ENGINE_ROOT outside home"; exit 64; }

usage() {
  cat <<USAGE
Usage:
  hci_local.sh --pack <path/to/*.pack.json> [--client <path/to/*.client.txt|AUTO>]

Examples:
  hci_local.sh --pack "/.../40._Miley..._pack.json" --client AUTO
  hci_local.sh --pack "/.../track_xxx.pack.json" --client "/.../track_xxx.client.txt"

Notes:
  - Uses AudioTools venv: $PY
  - Searches ENGINE_ROOT for package or advisor_cli.py:
      ENGINE_ROOT=$ENGINE_ROOT
      PACKAGE_NAME=$PACKAGE_NAME
USAGE
}

PACK=""
CLIENT="AUTO"

# --- parse args ---
while (( "$#" )); do
  case "$1" in
    --pack) PACK="$2"; shift 2;;
    --client)  CLIENT="$2";  shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; usage; exit 64;;
  esac
done

[ -f "$PACK" ] || { echo "ERROR: pack not found: $PACK" >&2; exit 66; }
PACK_DIR="$(cd "$(dirname "$PACK")" && pwd)"
[ "$CLIENT" = "AUTO" ] && CLIENT="$(ls "$PACK_DIR"/*client*.txt 2>/dev/null | head -n1 || true)"
[ -f "$CLIENT" ] || { echo "ERROR: client rich not found (value='$CLIENT')" >&2; exit 66; }

# --- discover CLI path for fallback ---
CLI_PATH="$(find "$ENGINE_ROOT" -type f -name 'advisor_cli.py' -path '*/CLI/*' -print -quit 2>/dev/null || true)"

# --- make package import-friendly (best effort) ---
PKG_DIR_CANDIDATE=""
if [ -n "$CLI_PATH" ]; then
  PKG_DIR_CANDIDATE="$(dirname "$(dirname "$CLI_PATH")")"
  [ -f "$PKG_DIR_CANDIDATE/__init__.py" ]       || : > "$PKG_DIR_CANDIDATE/__init__.py"
  [ -d "$PKG_DIR_CANDIDATE/CLI" ]  && [ -f "$PKG_DIR_CANDIDATE/CLI/__init__.py" ]   || { [ -d "$PKG_DIR_CANDIDATE/CLI" ] && : > "$PKG_DIR_CANDIDATE/CLI/__init__.py"; }
  [ -d "$PKG_DIR_CANDIDATE/Core" ] && [ -f "$PKG_DIR_CANDIDATE/Core/__init__.py" ]  || { [ -d "$PKG_DIR_CANDIDATE/Core" ] && : > "$PKG_DIR_CANDIDATE/Core/__init__.py"; }
fi

# --- try module import first ---
ENGINE_STDOUT="$(mktemp)"
ENGINE_STDERR="$(mktemp)"
EXPORT_JSON="$(mktemp)"
cleanup() { rm -f "$ENGINE_STDOUT" "$ENGINE_STDERR" "$EXPORT_JSON"; }
trap cleanup EXIT

# Prefer module import if possible
PYTHONPATH="$ENGINE_ROOT${PKG_DIR_CANDIDATE:+:$PKG_DIR_CANDIDATE}" \
"$PY" -m "$PACKAGE_NAME.CLI.advisor_cli" \
  --pack "$PACK" \
  --client  "$CLIENT" \
  --export "$EXPORT_JSON" \
  --print-audit >"$ENGINE_STDOUT" 2>"$ENGINE_STDERR" || MODULE_RC=$? || true

if [ "${MODULE_RC:-0}" -ne 0 ]; then
  # Fallback to direct path execution (no package import required)
  if [ -n "$CLI_PATH" ]; then
    PYTHONPATH="$ENGINE_ROOT${PKG_DIR_CANDIDATE:+:$PKG_DIR_CANDIDATE}" \
    "$PY" "$CLI_PATH" \
      --pack "$PACK" \
      --client  "$CLIENT" \
      --export "$EXPORT_JSON" \
      --print-audit >"$ENGINE_STDOUT" 2>"$ENGINE_STDERR" || FALLBACK_RC=$? || true
  else
    echo "ERROR: could not import module ($PACKAGE_NAME) and no CLI found under $ENGINE_ROOT" >&2
    cat "$ENGINE_STDERR" >&2
    exit 1
  fi
fi

RC="${FALLBACK_RC:-${MODULE_RC:-0}}"
if [ "$RC" -ne 0 ]; then
  echo "ERROR: engine run failed (rc=$RC)" >&2
  echo "--- STDERR (last 80 lines) ---" >&2
  tail -n 80 "$ENGINE_STDERR" >&2
  exit "$RC"
fi

# --- capture JSON (print-audit prints a JSON blob) ---
# Prefer stdout JSON; if not present, try the export file.
JSON_RAW="$(cat "$ENGINE_STDOUT")"
if ! echo "$JSON_RAW" | grep -q '{'; then
  JSON_RAW="$(cat "$EXPORT_JSON" 2>/dev/null || true)"
fi
if ! echo "$JSON_RAW" | grep -q '{'; then
  echo "ERROR: no JSON detected from engine output" >&2
  exit 1
fi

# --- print compact summary + full JSON ---
SUMMARY="$(/usr/bin/python3 - <<'PY' 2>/dev/null || true
import json, re, sys
data=sys.stdin.read()
m=re.search(r'\{.*\}', data, re.S)
if not m:
    print("??|?|?", end="")
    sys.exit(0)
obj=json.loads(m.group(0))
h=obj.get("HCI_v1",{})
print(f"{h.get('HCI_v1_score','?')}|{h.get('Market','?')}|{h.get('Emotional','?')}", end="")
PY
<<<"$JSON_RAW")"

printf "HCI|Market|Emotional: %s\n\n" "$SUMMARY"
# dump the JSON (so you can pipe > file if you want)
echo "$JSON_RAW"
