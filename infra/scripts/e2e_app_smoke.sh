#!/usr/bin/env bash
set -euo pipefail

# End-to-end app smoke:
# 1) generate a 1s tone
# 2) run ma_audio_engine.pipe_cli via module entrypoint
# 3) run advisor_host CLI on a sample client payload

PYTHON_BIN="${PYTHON:-python3}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_ROOT="$(mktemp -d -t ma_e2e_XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT

echo "[e2e] temp root: $TMP_ROOT"

TONE="$TMP_ROOT/tone.wav"
ADVISORY="$TMP_ROOT/advisory.json"
HOST_OUT="$TMP_ROOT/host_out.json"

# 1) Generate tone
"$PYTHON_BIN" - <<'PY'
import math, wave, struct, sys
tone = sys.argv[1]
sr = 44100
dur = 1.0
n = int(sr * dur)
with wave.open(tone, "w") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr)
    for i in range(n):
        w.writeframes(struct.pack("<h", int(0.2*32767*math.sin(2*math.pi*440*i/sr))))
PY "$TONE"
echo "[e2e] tone generated -> $TONE"

# 2) Run pipeline
echo "[e2e] running ma_audio_engine.pipe_cli"
"$PYTHON_BIN" -m ma_audio_engine.pipe_cli \
  --audio "$TONE" \
  --market 0.48 \
  --emotional 0.67 \
  --round 3 \
  --out "$ADVISORY"

test -s "$ADVISORY"
echo "[e2e] advisory written -> $ADVISORY"

# 3) Run host CLI on sample client payload
SAMPLE_CLIENT="$REPO_ROOT/hosts/advisor_host/tests/fixtures/sample_client.json"
if [[ ! -f "$SAMPLE_CLIENT" ]]; then
  echo "[e2e] sample client payload missing at $SAMPLE_CLIENT" >&2
  exit 1
fi
echo "[e2e] running advisor_host CLI on sample_client.json"
PYTHONPATH="$REPO_ROOT/hosts/advisor_host_core/src:$REPO_ROOT/hosts/advisor_host" \
  "$PYTHON_BIN" "$REPO_ROOT/hosts/advisor_host/cli/ma_host.py" \
  "$SAMPLE_CLIENT" > "$HOST_OUT"

test -s "$HOST_OUT"
echo "[e2e] host output -> $HOST_OUT"
echo "[e2e] done"
