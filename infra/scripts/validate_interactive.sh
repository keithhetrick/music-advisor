#!/usr/bin/env bash
# Interactive validator runner (macOS bash 3.2 compatible)
# Picks:
#   1) ROOT dir (defaults to your 2025 features_output path)
#   2) a PACK JSON
#   3) a client policy file
#   4) optional policy-bypass (forces use_ttc/use_exposures via temp copy)
#   5) runs verbose validator and prints JSON to STDOUT

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

ROOT_DEFAULT="${ROOT_DEFAULT:-$HOME/music-advisor/features_output/2025}"

die() { echo "ERROR: $*" >&2; exit 1; }

ask_root_dir() {
  echo "Choose ROOT directory to search under:"
  echo "  1) $ROOT_DEFAULT"
  echo "  2) Current directory: $PWD"
  echo "  3) Enter a custom absolute/relative path"
  read -r -p "Select [1/2/3]: " sel
  case "$sel" in
    1) ROOT="$ROOT_DEFAULT" ;;
    2) ROOT="$PWD" ;;
    3) read -r -p "Enter path: " ROOT ;;
    *) echo "Invalid, defaulting to 1"; ROOT="$ROOT_DEFAULT" ;;
  esac
  [[ -d "$ROOT" ]] || die "Root directory does not exist: $ROOT"
  ROOT="$(cd "$ROOT" && pwd)"
  require_safe_subpath "$ROOT_DEFAULT/.." "$ROOT" || die "Root outside allowed base"
  echo "ROOT = $ROOT"
}

# Pass items as args: select_from_list "Prompt" "${array[@]}"
select_from_list() {
  local prompt="$1"; shift
  local items=( "$@" )
  local count="${#items[@]}"

  echo
  echo "$prompt"
  if (( count == 0 )); then
    echo "No items found." >&2
    return 1
  fi

  local i=1
  while (( i <= count )); do
    printf "%3d) %s\n" "$i" "${items[$((i-1))]}"
    i=$((i+1))
  done
  echo "  q) cancel"

  while true; do
    read -r -p "Choose number: " idx
    if [[ "$idx" == "q" ]]; then return 1; fi
    if [[ "$idx" =~ ^[0-9]+$ ]] && (( idx>=1 && idx<=count )); then
      CHOICE="${items[$((idx-1))]}"   # global CHOICE
      echo "Selected: $CHOICE"
      return 0
    fi
    echo "Invalid selection."
  done
}

gather_packs() {
  local root="$1"
  PACKS=()
  # Prefer *.pack.json
  while IFS= read -r path; do PACKS+=( "$path" ); done < <(find "$root" -type f -name '*.pack.json' 2>/dev/null | sort)
  # Fallback to *pack*.json or *datapack*.json
  if (( ${#PACKS[@]} == 0 )); then
    while IFS= read -r path; do PACKS+=( "$path" ); done < <(find "$root" -type f \( -name '*pack*.json' -o -name '*datapack*.json' \) 2>/dev/null | sort)
  fi
  # Optionally all *.json
  if (( ${#PACKS[@]} == 0 )); then
    echo "No pack-like JSON files found."
    read -r -p "Search ALL *.json under $root? [y/N]: " yn
    if echo "$yn" | grep -qi '^y'; then
      while IFS= read -r path; do PACKS+=( "$path" ); done < <(find "$root" -type f -name '*.json' 2>/dev/null | sort)
    fi
  fi
}

gather_clients() {
  local root="$1"
  CLIENTS=()
  while IFS= read -r path; do CLIENTS+=( "$path" ); done < <(find "$root" -type f -iname '*client*.txt' 2>/dev/null | sort)
}

pick_pack_file() {
  echo; echo "Searching for candidate PACK files under: $ROOT"
  gather_packs "$ROOT"
  select_from_list "Select a PACK JSON:" "${PACKS[@]}" || die "Cancelled."
  PACK="$CHOICE"
}

pick_client_file() {
  echo; echo "Searching for client policy files under: $ROOT"
  gather_clients "$ROOT"
  (( ${#CLIENTS[@]} > 0 )) || die "No client*.txt files found under $ROOT"
  select_from_list "Select a client policy file:" "${CLIENTS[@]}" || die "Cancelled."
  CLIENT="$CHOICE"
}

confirm_bypass() {
  echo
  echo "Bypass policy? (forces use_ttc=true, use_exposures=true via temp copy)"
  read -r -p "[y/N]: " yn
  if echo "$yn" | grep -qi '^y'; then
    BYPASS=1
  else
    BYPASS=0
  fi
}

make_bypass_copy() {
  local src="$1"
  local dst="/tmp/$(basename "$src").bypass.txt"
  python3 - "$src" > "$dst" << 'PY'
import sys, re
path=sys.argv[1]
txt=open(path, encoding="utf-8", errors="ignore").read()
def force_flag(line, key):
    if "STRUCTURE_POLICY" not in line: return line
    if re.search(rf"{key}\s*=\s*true", line): return line
    if re.search(rf"{key}\s*=\s*false", line):
        return re.sub(rf"{key}\s*=\s*false", f"{key}=true", line)
    sep = " | " if "|" in line else " "
    return line + f"{sep}{key}=true"
out=[]
for ln in txt.splitlines():
    if "STRUCTURE_POLICY" in ln:
        ln = force_flag(ln, "use_ttc")
        ln = force_flag(ln, "use_exposures")
    out.append(ln)
print("\n".join(out))
PY
  echo "$dst"
}

run_validator() {
  local pack="$1" client="$2"
  command -v python3 >/dev/null 2>&1 || die "python3 not found."
  [[ -f tools/validator/verbose_validator.py ]] || die "Missing tools/validator/verbose_validator.py"
  echo; echo ">>> Running verbose validator"; echo "PACK: $pack"; echo " CLIENT: $client"; echo
  python3 tools/validator/verbose_validator.py "$pack" "$client"
}

# ---- main ----
ask_root_dir
pick_pack_file
pick_client_file
confirm_bypass

if (( BYPASS == 1 )); then
  echo; echo "Creating temporary bypassed policy copy…"
  BYPASS_CLIENT="$(make_bypass_copy "$CLIENT")"
  echo "Bypassed client: $BYPASS_CLIENT"
  echo; echo "*** ORIGINAL POLICY AUDIT ***"
  run_validator "$PACK" "$CLIENT"
  echo; echo "*** BYPASS POLICY AUDIT ***"
  run_validator "$PACK" "$BYPASS_CLIENT"
else
  run_validator "$PACK" "$CLIENT"
fi
