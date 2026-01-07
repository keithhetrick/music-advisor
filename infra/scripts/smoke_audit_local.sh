#!/usr/bin/env zsh
# Local audit wrapper: runs smoke_full_chain with sensible defaults.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: infra/scripts/smoke_audit_local.sh [audio_path]

Env toggles:
  SMOKE_GEN_AUDIO=1                Generate test audio (default if no path provided)
  SMOKE_REQUIRE_SIDECAR=1          Require sidecar; fail on timeout/failure
  SMOKE_SIDECAR_TIMEOUT_SECONDS=90 Override sidecar timeout
  SMOKE_SIDECAR_RETRY_ATTEMPTS=1   Override sidecar retries
  SMOKE_VALIDATE=0                 Skip validator (default 1)
Examples:
  infra/scripts/smoke_audit_local.sh
  SMOKE_REQUIRE_SIDECAR=1 SMOKE_SIDECAR_TIMEOUT_SECONDS=120 infra/scripts/smoke_audit_local.sh /path/to/audio.wav
USAGE
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SMOKE="${SCRIPT_DIR}/smoke_full_chain.sh"

audio_arg=""
if [[ $# -ge 1 ]]; then
  audio_arg="$1"
else
  : ${SMOKE_GEN_AUDIO:=1}
fi

: ${SMOKE_VALIDATE:=1}
: ${SMOKE_REQUIRE_SIDECAR:=0}
: ${SMOKE_SIDECAR_TIMEOUT_SECONDS:=}
: ${SMOKE_SIDECAR_RETRY_ATTEMPTS:=}
: ${LOG_JSON:=0}

echo "[audit] SMOKE_GEN_AUDIO=${SMOKE_GEN_AUDIO:-0} SMOKE_REQUIRE_SIDECAR=${SMOKE_REQUIRE_SIDECAR:-0} SMOKE_SIDECAR_TIMEOUT_SECONDS=${SMOKE_SIDECAR_TIMEOUT_SECONDS:-} SMOKE_SIDECAR_RETRY_ATTEMPTS=${SMOKE_SIDECAR_RETRY_ATTEMPTS:-} SMOKE_VALIDATE=${SMOKE_VALIDATE:-1} LOG_JSON=${LOG_JSON:-0}"

if [[ -n "$audio_arg" ]]; then
  exec "$SMOKE" "$audio_arg"
else
  exec "$SMOKE"
fi
