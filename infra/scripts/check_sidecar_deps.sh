#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

# Quick dependency preflight for the sidecar toolchain.
# - Verifies the expected venv python exists
# - Ensures NumPy < 2 (Essentia wheels need it on this machine)
# - Ensures SciPy and librosa are in expected ranges (API stability)
# - Ensures Essentia imports cleanly
# - Madmom is optional; we warn if missing

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY_BIN="${PY_BIN:-$PROJECT_ROOT/.venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  echo "[sidecar:deps] ERROR: python not found at $PY_BIN" >&2
  exit 1
fi

echo "[sidecar:deps] python: $PY_BIN"

read -r np_ver np_ok sp_ver sp_ok lb_ver lb_ok <<<"$( "$PY_BIN" - <<'PY'
import importlib
def lt2(v):
    parts = [int(p) for p in v.split(".")[:2]]
    return (parts[0], parts[1]) < (2, 0)
def in_range(v, low, high):
    parts = [int(p) for p in v.split(".")[:2]]
    return (parts[0], parts[1]) >= low and (parts[0], parts[1]) < high
np_ver = importlib.import_module("numpy").__version__
sp_ver = importlib.import_module("scipy").__version__
lb_ver = importlib.import_module("librosa").__version__
np_ok = "ok" if lt2(np_ver) else "fail"
sp_ok = "ok" if in_range(sp_ver, (1,9), (1,12)) else "fail"
lb_ok = "ok" if in_range(lb_ver, (0,10), (0,11)) else "fail"
print(np_ver, np_ok, sp_ver, sp_ok, lb_ver, lb_ok)
PY
)"

if [[ "$np_ok" != "ok" ]]; then
  echo "[sidecar:deps] ERROR: NumPy $np_ver detected (need < 2.0 for Essentia wheel)" >&2
  exit 1
fi
echo "[sidecar:deps] numpy $np_ver (ok)"

if [[ "$sp_ok" != "ok" ]]; then
  echo "[sidecar:deps] ERROR: SciPy $sp_ver detected (need >=1.9,<1.12)" >&2
  exit 1
fi
echo "[sidecar:deps] scipy $sp_ver (ok)"

if [[ "$lb_ok" != "ok" ]]; then
  echo "[sidecar:deps] ERROR: librosa $lb_ver detected (need >=0.10,<0.11)" >&2
  exit 1
fi
echo "[sidecar:deps] librosa $lb_ver (ok)"

# Essentia is required
ALLOW_MISSING_ESSENTIA="${ALLOW_MISSING_ESSENTIA:-0}"
if ! "$PY_BIN" - <<'PY' >/dev/null 2>&1; then
import essentia.standard as es  # noqa: F401
print("essentia ok")
PY
  if [[ "$ALLOW_MISSING_ESSENTIA" == "1" ]]; then
    echo "[sidecar:deps] WARN: Essentia import failed (ALLOW_MISSING_ESSENTIA=1; will fall back to other backends)" >&2
  else
    echo "[sidecar:deps] ERROR: Essentia import failed" >&2
    exit 1
  fi
else
  echo "[sidecar:deps] essentia import ok"
fi

# Madmom is optional; warn only
if "$PY_BIN" - <<'PY' >/dev/null 2>&1; then
import madmom  # noqa: F401
PY
  echo "[sidecar:deps] madmom import ok"
else
  # Optional dep; warn to stdout so Automator doesn't treat it as failure
  echo "[sidecar:deps] WARN: madmom not importable (optional)"
fi

echo "[sidecar:deps] ready"
