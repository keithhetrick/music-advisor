#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib_security.sh"

# Dependency preflight for the main pipeline (librosa path).
# - Ensures expected venv python exists
# - Checks NumPy, SciPy, librosa versions are within supported ranges
# - Warns on optional deps only if desired; hard fails on core ranges

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY_BIN="${PY_BIN:-$PROJECT_ROOT/.venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  echo "[pipeline:deps] ERROR: python not found at $PY_BIN" >&2
  exit 1
fi

echo "[pipeline:deps] python: $PY_BIN"

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
  echo "[pipeline:deps] ERROR: NumPy $np_ver detected (need < 2.0)" >&2
  exit 1
fi
echo "[pipeline:deps] numpy $np_ver (ok)"

if [[ "$sp_ok" != "ok" ]]; then
  echo "[pipeline:deps] ERROR: SciPy $sp_ver detected (need >=1.9,<1.12)" >&2
  exit 1
fi
echo "[pipeline:deps] scipy $sp_ver (ok)"

if [[ "$lb_ok" != "ok" ]]; then
  echo "[pipeline:deps] ERROR: librosa $lb_ver detected (need >=0.10,<0.11)" >&2
  exit 1
fi
echo "[pipeline:deps] librosa $lb_ver (ok)"

echo "[pipeline:deps] ready"
