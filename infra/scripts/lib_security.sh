#!/usr/bin/env bash
# Shared shell security helpers (POSIX-ish).
# Source this in scripts that handle user-provided paths to avoid traversal
# and to wrap destructive commands safely.

set -euo pipefail

require_safe_subpath() {
  # require_safe_subpath <base> <path>
  local base="$1"; shift
  local target="$1"; shift
  local base_abs target_abs
  base_abs="$(cd "$base" 2>/dev/null && pwd)" || return 1
  target_abs="$(cd "$target" 2>/dev/null && pwd)" || return 1
  case "$target_abs" in
    "$base_abs"/*|"$base_abs") return 0 ;;
    *) echo "[SECURITY] path outside allowed root: $target_abs (base: $base_abs)" >&2; return 64 ;;
  esac
}

safe_rm() {
  # safe_rm <path>
  require_safe_subpath "${2:-/}" "${1:?path required}" || exit $?
  rm -- "$1"
}

safe_mv() {
  # safe_mv <src> <dst> (dst must be under base provided in $3)
  local src="$1"; local dst="$2"; local base="${3:-/}"
  require_safe_subpath "$base" "$dst" || exit $?
  mv -- "$src" "$dst"
}
