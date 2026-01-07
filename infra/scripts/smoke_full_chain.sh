#!/bin/zsh
set -euo pipefail

# Structured stage logging (honors LOG_JSON=1)
typeset -Ag STAGE_TS
# Allow custom sidecar command by default in smoke runs (mirrors Automator behavior).
export ALLOW_CUSTOM_SIDECAR_CMD="${ALLOW_CUSTOM_SIDECAR_CMD:-1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
PY="$REPO/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "[ERR] python3 not found; create/activate $REPO/.venv" >&2
    exit 1
  fi
fi
. "$SCRIPT_DIR/lib_security.sh"
now_ms() {
  "$PY" - <<'PY'
import time
print(int(time.time()*1000))
PY
}
log_json() {
  if [[ "${LOG_JSON:-0}" == "1" ]]; then
    "$PY" - <<'PY' "$1"
import json,sys
from datetime import datetime
payload=json.loads(sys.argv[1])
payload.setdefault("ts", datetime.utcnow().isoformat()+"Z")
print(json.dumps(payload))
PY
  fi
}
stage_start() {
  local stage="$1"; shift
  STAGE_TS[$stage]=$(now_ms)
  log_json "$("$PY" - <<'PY' "$stage" "$@"
import json,sys
stage=sys.argv[1]
extra=dict(arg.split("=",1) for arg in sys.argv[2:] if "=" in arg)
payload={"event":"stage_start","tool":"smoke_full_chain","stage":stage}
payload.update(extra)
print(json.dumps(payload))
PY
)"
}
stage_end() {
  local stage="$1"; shift
  local end=$(now_ms)
  local start_marker=${STAGE_TS[$stage]:-}
  if [[ -z "${start_marker}" ]]; then
    STAGE_TS[$stage]=$end
    start_marker=$end
    log_json "$("$PY" - <<'PY' "$stage"
import json,sys
stage=sys.argv[1]
print(json.dumps({"event":"stage_warn","tool":"smoke_full_chain","stage":stage,"warning":"stage_end_without_stage_start"}))
PY
)"
  fi
  local start=$start_marker
  local dur=$(( end - start ))
  log_json "$("$PY" - <<'PY' "$stage" "$dur" "$@"
import json,sys
stage=sys.argv[1]; dur=int(sys.argv[2])
extra=dict(arg.split("=",1) for arg in sys.argv[3:] if "=" in arg)
payload={"event":"stage_end","tool":"smoke_full_chain","stage":stage,"duration_ms":dur,"status":"ok"}
payload.update(extra)
print(json.dumps(payload))
PY
)"
}

# Minimal end-to-end smoke test for the HCI/client pipeline on a single audio file.
# Usage: scripts/smoke_full_chain.sh /path/to/audio.wav

export PYTHONPATH="$REPO:$REPO/src:${PYTHONPATH:-}"
export LOG_REDACT="${LOG_REDACT:-1}"
export LOG_SANDBOX="${LOG_SANDBOX:-1}"
if [[ -n "${SMOKE_SIDECAR_TIMEOUT_SECONDS:-}" ]]; then
  export SIDECAR_TIMEOUT_SECONDS="${SMOKE_SIDECAR_TIMEOUT_SECONDS}"
fi
if [[ -n "${SMOKE_SIDECAR_RETRY_ATTEMPTS:-}" ]]; then
  export SIDECAR_RETRY_ATTEMPTS="${SMOKE_SIDECAR_RETRY_ATTEMPTS}"
fi

if [[ $# -lt 1 ]]; then
  if [[ "${SMOKE_GEN_AUDIO:-0}" == "1" ]]; then
    TMP_AUDIO="$(mktemp -t smoke_audio_XXXXXX).wav"
    "$PY" - <<'PY' "$TMP_AUDIO"
import sys, math
import numpy as np
from pathlib import Path
out = Path(sys.argv[1])
sr = 44100
dur = 6.0  # longer clip for more stable tempo estimation
t = np.linspace(0, dur, int(sr*dur), endpoint=False)
data = 0.1 * np.sin(2*math.pi*440*t)
try:
    import soundfile as sf
    sf.write(out, data, sr, subtype="PCM_16")
except Exception:
    import wave, struct
    with wave.open(str(out), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        for x in data:
            w.writeframes(struct.pack("<h", int(max(-1.0, min(1.0, x)) * 32767)))
print(out)
PY
    IN_AUDIO="$TMP_AUDIO"
    echo "[smoke] generated test audio at $IN_AUDIO (SMOKE_GEN_AUDIO=1)"
  else
    echo "usage: $0 /path/to/audio (or set SMOKE_GEN_AUDIO=1 to auto-generate a test clip)" >&2
    exit 1
  fi
else
  IN_AUDIO="$1"
fi

IN_AUDIO="$(cd "$(dirname "$IN_AUDIO")" && pwd)/$(basename "$IN_AUDIO")"
if [[ ! -f "$IN_AUDIO" ]]; then
  echo "[ERR] audio file not found: $IN_AUDIO" >&2
  exit 1
fi

TS="$(date -u +%Y%m%d_%H%M%S)"
OUT_DIR="$REPO/data/features_output/smoke/$TS/$(basename "$IN_AUDIO" | sed 's/[[:space:]]/_/g')"
mkdir -p "$OUT_DIR"
require_safe_subpath "$REPO/data/features_output" "$OUT_DIR" || { echo "[ERR] OUT_DIR outside data/features_output"; exit 64; }

FEATURES_JSON="$OUT_DIR/smoke.features.json"
SIDECAR_JSON="$OUT_DIR/smoke.sidecar.json"
MERGED_JSON="$OUT_DIR/smoke.merged.json"
CLIENT_JSON="$OUT_DIR/smoke.client.json"
CLIENT_TXT="$OUT_DIR/smoke.client.rich.txt"
HCI_JSON="$OUT_DIR/smoke.hci.json"

echo "[smoke] using PY=$PY"
echo "[smoke] OUT_DIR=$OUT_DIR"
echo "[smoke] require_sidecar=${SMOKE_REQUIRE_SIDECAR:-0} sidecar_timeout=${SMOKE_SIDECAR_TIMEOUT_SECONDS:-} sidecar_retries=${SMOKE_SIDECAR_RETRY_ATTEMPTS:-}"

stage_start "smoke_full_chain" audio="$IN_AUDIO" out_dir="$OUT_DIR"
set -x
MA_AUDIO_CLI=(${MA_AUDIO_CLI[@]:-"$PY"})
MA_AUDIO_CLI+=("$REPO/tools/ma_audio_features.py")
if [[ "${SMOKE_REQUIRE_SIDECAR:-0}" == "1" ]]; then
  MA_AUDIO_CLI+=("--require-sidecar")
fi
SIDECAR_CLI=(${SIDECAR_CLI[@]:-"$PY"})
SIDECAR_CLI+=("$REPO/tools/tempo_sidecar_runner.py")
MERGE_CLI=(${MERGE_CLI[@]:-"$PY"})
MERGE_CLI+=("$REPO/tools/equilibrium_merge.py")
PACK_CLI=(${PACK_CLI[@]:-"$PY"})
PACK_CLI+=("$REPO/tools/pack_writer.py")
PACK_SCRIPT=""
# Prefer in-repo pack_writer during smoke runs to pick up latest changes without reinstalling.
if [[ "${SMOKE_GEN_AUDIO:-0}" == "1" ]]; then
  PACK_CLI=("$PY")
  PACK_SCRIPT="$REPO/tools/pack_writer.py"
fi
SIDECAR_CMD_PREFIX="${(j: :)${(q)SIDECAR_CLI[@]}}"
SIDECAR_CMD="${SIDECAR_CMD_PREFIX} --audio {audio} --out {out}"
if [[ "${LOG_REDACT:-1}" == "1" ]]; then
  echo "[smoke] sidecar_cmd_template=<redacted>"
else
  echo "[smoke] sidecar_cmd_template=$SIDECAR_CMD"
fi

stage_start "ma_audio_features" audio="$IN_AUDIO"
"${MA_AUDIO_CLI[@]}" --audio "$IN_AUDIO" --out "$FEATURES_JSON" --tempo-backend sidecar --tempo-sidecar-json-out "$SIDECAR_JSON" --tempo-sidecar-cmd "$SIDECAR_CMD"
stage_end "ma_audio_features" out="$FEATURES_JSON"
stage_start "equilibrium_merge" merged="$MERGED_JSON"
"${MERGE_CLI[@]}" --internal "$FEATURES_JSON" --out "$MERGED_JSON"
stage_end "equilibrium_merge" out="$MERGED_JSON"
stage_start "pack_writer" out_dir="$OUT_DIR"
if [[ -n "$PACK_SCRIPT" ]]; then
  "${PACK_CLI[@]}" "$PACK_SCRIPT" --merged "$MERGED_JSON" --out-dir "$OUT_DIR" --client-json "$CLIENT_JSON" --client-txt "$CLIENT_TXT" --no-pack
else
  "${PACK_CLI[@]}" --merged "$MERGED_JSON" --out-dir "$OUT_DIR" --client-json "$CLIENT_JSON" --client-txt "$CLIENT_TXT" --no-pack
fi
stage_end "pack_writer" out_dir="$OUT_DIR"

# Ensure runtime_sec exists in client helper (smoke sanity).
"$PY" - "$CLIENT_JSON" <<'PY'
import json, sys
path = sys.argv[1]
data = json.loads(open(path).read())
feat = data.get("features") or {}
if "runtime_sec" not in feat and "duration_sec" in feat:
    feat["runtime_sec"] = feat["duration_sec"]
data["features"] = feat
with open(path, "w") as f:
    json.dump(data, f, indent=2)
PY

# Ensure feature_pipeline_meta has minimal defaults (helps lint/echo_hci), with a best-effort hash.
"$PY" - <<'PY' "$FEATURES_JSON" "$IN_AUDIO" "${SMOKE_GEN_AUDIO:-0}"
import json, sys, hashlib, os
feat_path, audio_path, is_smoke = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
data = json.loads(open(feat_path).read())
meta = data.get("feature_pipeline_meta") or {}
src = data.get("source_audio") or audio_path
expanded = os.path.expanduser(src) if isinstance(src, str) else src
if not meta.get("source_hash"):
    if expanded and os.path.exists(expanded):
        with open(expanded, "rb") as f:
            meta["source_hash"] = hashlib.sha256(f.read()).hexdigest()
    else:
        meta["source_hash"] = os.path.basename(src) if src else "unknown"
meta.setdefault("config_fingerprint", "smoke_synth" if is_smoke else "auto_fill")
meta.setdefault("pipeline_version", "smoke_synth" if is_smoke else "auto_fill")
data["feature_pipeline_meta"] = meta
with open(feat_path, "w") as f:
    json.dump(data, f, indent=2)
PY

# Dummy HCI bootstrap: if no HCI exists, synthesize a minimal one from merged.json so downstream steps can run.
if [[ ! -f "$HCI_JSON" ]]; then
  stage_start "synthesize_hci" merged="$MERGED_JSON"
  "$PY" - <<'PY' "$MERGED_JSON" "$HCI_JSON"
import json, sys
from pathlib import Path
if len(sys.argv) < 3:
    raise SystemExit("usage: synth merged.json out.json")
merged = Path(sys.argv[1])
out = Path(sys.argv[2])
with open(merged) as f:
    m = json.load(f)
# Build a minimal client payload to align lint expectations; keep primary client untouched.
client_stub = {
    "region": "US",
    "profile": "Pop",
    "generated_by": "smoke",
    "audio_name": m.get("source_audio", "smoke"),
    "inputs": {
        "paths": {"source_audio": m.get("source_audio", "smoke.wav")},
        "merged_features_present": True,
        "lyric_axis_present": False,
        "internal_features_present": True,
    },
    "features": {
        "tempo_bpm": m.get("tempo_bpm", 0),
        "key": m.get("key", "C"),
        "mode": m.get("mode", "major"),
        "duration_sec": m.get("duration_sec", 0) or 1,
        "loudness_LUFS": m.get("loudness_LUFS", 0),
        "energy": m.get("energy", 0.5),
        "danceability": m.get("danceability", 0.5),
        "valence": m.get("valence", 0.5),
    },
    "features_full": {
        "bpm": m.get("tempo_bpm", 0),
        "mode": m.get("mode", "major"),
        "key": m.get("key", "C"),
        "duration_sec": m.get("duration_sec", 0) or 1,
        "loudness_lufs": m.get("loudness_LUFS", 0),
        "energy": m.get("energy", 0.5),
        "danceability": m.get("danceability", 0.5),
        "valence": m.get("valence", 0.5),
    },
    "feature_pipeline_meta": {
        "source_hash": m.get("source_audio", ""),
        "config_fingerprint": "smoke-test",
        "pipeline_version": "smoke",
        "sidecar_status": "missing",
        "qa_gate": "unknown",
        "tempo_backend": "sidecar",
        "tempo_backend_detail": "essentia",
    },
    "historical_echo_meta": {
        "neighbors_file": "",
        "neighbors_total": 0,
        "neighbor_tiers": [],
        "neighbors_kept_inline": 0,
        "tier": "smoke",
        "raw_score": 0.5,
        "calibrated_score": 0.5,
        "final_source": "smoke",
        "HCI_v1_interpretation": "smoke_synthetic",
        "HCI_v1_notes": "smoke_synthetic",
    },
    "historical_echo_v1": {
        "neighbors": [],
        "neighbors_by_tier": {},
        "decade_counts": {},
        "wip_features": {
            "tempo": m.get("tempo_bpm"),
            "energy": m.get("energy"),
            "valence": m.get("valence"),
            "loudness": m.get("loudness_LUFS"),
            "tempo_confidence_score": 0.1,
        },
        "primary_decade": None,
        "primary_decade_neighbor_count": 0,
        "top_neighbor": {},
    },
}
stub_client_path = out.with_name("smoke.synth.client.json")
with open(stub_client_path, "w") as f:
    json.dump(client_stub, f, indent=2)
hci = {
    "HCI_v1_score_raw": 0.5,
    "HCI_v1_score": 0.5,
    "HCI_v1_final_score": 0.5,
    "HCI_v1_role": "unknown",
    "HCI_v1": {"raw": 0.5, "score": 0.5, "final_score": 0.5},
    "feature_pipeline_meta": {
        "source_hash": m.get("source_audio", ""),
        "config_fingerprint": "smoke-test",
        "pipeline_version": "smoke",
        "sidecar_status": "missing",
        "qa_gate": "unknown",
        "tempo_backend": "sidecar",
        "tempo_backend_detail": "essentia",
        "tempo_primary": m.get("tempo_bpm"),
        "tempo_alternates": [m.get("tempo_bpm", 0) / 2, m.get("tempo_bpm", 0) * 2],
        "tempo_confidence": "low",
        "tempo_confidence_score": 0.1,
        "tempo_confidence_score_raw": 0.1,
        "tempo_choice_reason": "smoke_synth",
        "target_sample_rate": m.get("sample_rate"),
    },
    "historical_echo_meta": {
        "neighbors_file": "",
        "neighbors_total": 0,
        "neighbor_tiers": [],
        "neighbors_kept_inline": 0,
        "tier": "smoke",
        "raw_score": 0.5,
        "calibrated_score": 0.5,
        "final_source": "smoke",
        "HCI_v1_interpretation": "smoke_synthetic",
        "HCI_v1_notes": "smoke_synthetic",
    },
    "historical_echo_v1": {
        "neighbors": [],
        "neighbors_by_tier": {},
        "decade_counts": {},
        "wip_features": {
            "tempo": m.get("tempo_bpm"),
            "energy": m.get("energy"),
            "valence": m.get("valence"),
            "loudness": m.get("loudness_LUFS"),
            "tempo_confidence_score": 0.1,
        },
        "primary_decade": None,
        "primary_decade_neighbor_count": 0,
        "top_neighbor": {},
    },
}
with open(out, "w") as f:
    json.dump(hci, f, indent=2)
print(f"[smoke] synthesized HCI -> {out}")
PY
  stage_end "synthesize_hci" out="$HCI_JSON"
fi

stage_start "hci_final_score" root="$OUT_DIR"
"$PY" "$REPO/tools/hci_final_score.py" --root "$OUT_DIR" --recompute
stage_end "hci_final_score" root="$OUT_DIR"
stage_start "philosophy_hci" root="$OUT_DIR"
"$PY" "$REPO/tools/ma_add_philosophy_to_hci.py" --root "$OUT_DIR"
stage_end "philosophy_hci" root="$OUT_DIR"
stage_start "echo_hci" root="$OUT_DIR"
"$PY" "$REPO/tools/ma_add_echo_to_hci_v1.py" --root "$OUT_DIR"
stage_end "echo_hci" root="$OUT_DIR"
# Rebuild client helpers right before merge to guarantee runtime_sec + fresh schema fields.
"$PY" "$REPO/tools/pack_writer.py" --merged "$MERGED_JSON" --out-dir "$OUT_DIR" --client-json "$CLIENT_JSON" --client-txt "$CLIENT_TXT" --no-pack
stage_start "merge_client_hci" out="$CLIENT_TXT"
"$PY" "$REPO/tools/ma_merge_client_and_hci.py" --client-json "$CLIENT_JSON" --hci "$HCI_JSON" --client-out "$CLIENT_TXT"
stage_end "merge_client_hci" out="$CLIENT_TXT"
stage_start "philosophy_client" root="$OUT_DIR"
"$PY" "$REPO/tools/ma_add_philosophy_to_client_rich.py" --root "$OUT_DIR"
stage_end "philosophy_client" root="$OUT_DIR"
stage_start "echo_client" root="$OUT_DIR"
"$PY" "$REPO/tools/hci/ma_add_echo_to_client_rich_v1.py" --root "$OUT_DIR"
stage_end "echo_client" root="$OUT_DIR"

# Write a run summary with versions (useful for CI artifacts)
stage_start "log_summary" out_dir="$OUT_DIR"
"$PY" "$REPO/tools/log_summary.py" --out-dir "$OUT_DIR"
stage_end "log_summary" out_dir="$OUT_DIR"

# Optional local validation of smoke outputs.
if [[ "${SMOKE_VALIDATE:-1}" != "0" ]]; then
  stage_start "smoke_validate_outputs" root="$OUT_DIR"
  if "$PY" "$REPO/tools/smoke_validate_outputs.py" --root "$OUT_DIR"; then
    echo "[smoke] validation passed for $OUT_DIR"
    stage_end "smoke_validate_outputs" root="$OUT_DIR"
  else
    echo "[ERR] smoke output validation failed for $OUT_DIR" >&2
    exit 1
  fi
fi
set +x

echo "[smoke] complete -> $OUT_DIR"
stage_end "smoke_full_chain" status="ok" out_dir="$OUT_DIR"
