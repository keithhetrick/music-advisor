#!/usr/bin/env bash
set -euo pipefail

# --- auto logging (writes to logs/automator_*.log unless overridden) ---
LOG_DIR="${LOG_DIR:-${REPO:-$HOME/music-advisor}/logs}"
mkdir -p "$LOG_DIR"
AUTO_LOG="${AUTOMATOR_LOG:-$LOG_DIR/automator_$(date +%Y%m%d_%H%M%S).log}"
# Simple append logging to avoid /dev/fd restrictions in Automator
exec >>"$AUTO_LOG" 2>&1
echo "[INFO] Automator log -> $AUTO_LOG"

# Structured stage logging (honors LOG_JSON=1). Avoid associative arrays for POSIX shells.
STAGE_TS_FILE="$(mktemp -t automator_stage_ts.XXXXXX)"
now_ms() {
  python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}
log_json() {
  if [[ "${LOG_JSON:-0}" == "1" ]]; then
    python3 - <<'PY' "$@"
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
  local ts=$(now_ms)
  printf "%s=%s\n" "$stage" "$ts" >> "$STAGE_TS_FILE"
  log_json "$(python3 - <<'PY' "$stage" "$@"
import json,sys
stage=sys.argv[1]
extra=dict(arg.split("=",1) for arg in sys.argv[2:] if "=" in arg)
payload={"event":"stage_start","tool":"automator","stage":stage}
payload.update(extra)
print(json.dumps(payload))
PY
)"
}
stage_end() {
  local stage="$1"; shift
  local end=$(now_ms)
  local start=$(grep "^${stage}=" "$STAGE_TS_FILE" | tail -n1 | cut -d= -f2)
  start=${start:-0}
  local dur=$(( end - start ))
  log_json "$(python3 - <<'PY' "$stage" "$dur" "$@"
import json,sys
stage=sys.argv[1]; dur=int(sys.argv[2])
extra=dict(arg.split("=",1) for arg in sys.argv[3:] if "=" in arg)
payload={"event":"stage_end","tool":"automator","stage":stage,"duration_ms":dur,"status":"ok"}
payload.update(extra)
if "status" in extra:
    payload["status"] = extra["status"]
print(json.dumps(payload))
PY
)"
}

# ---- Optional env overlay (config/automator.env) ----
AUTOMATOR_ENV="${AUTOMATOR_ENV:-${REPO:-$HOME/music-advisor}/config/automator.env}"
if [[ -f "$AUTOMATOR_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$AUTOMATOR_ENV"
fi

# ---- Repo + Python config ----
REPO="${REPO:-${MA_AUTOMATOR_REPO:-$HOME/music-advisor}}"
BIN_DIR="${BIN_DIR:-${MA_AUTOMATOR_BIN_DIR:-$REPO/.venv/bin}}"
export PATH="${MA_AUTOMATOR_PATH:-/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin}:$BIN_DIR:$PATH"
PY_BIN="${PY_BIN:-${MA_AUTOMATOR_PY_BIN:-$BIN_DIR/python}}"
SIDECAR_CMD_ENV="${MA_SIDECAR_CMD:-${MA_AUTOMATOR_SIDECAR_CMD:-}}"
# Allow custom sidecar command only if explicitly opted in.
# Allow custom sidecar command by default so the packaged template runs (matches Quick Action behavior).
export ALLOW_CUSTOM_SIDECAR_CMD="${ALLOW_CUSTOM_SIDECAR_CMD:-1}"
# Default timeout/limits for sidecar to avoid hangs.
export SIDECAR_TIMEOUT_SECONDS="${SIDECAR_TIMEOUT_SECONDS:-90}"
# Default to redacted/sandboxed logs in Automator runs; caller can override.
export LOG_REDACT="${LOG_REDACT:-1}"
export LOG_SANDBOX="${LOG_SANDBOX:-0}"
# Default confidence bounds to the calibrated Essentia window unless overridden
CONF_LOWER="${TEMPO_CONF_LOWER:-${MA_AUTOMATOR_CONF_LOWER:-0.9}}"
CONF_UPPER="${TEMPO_CONF_UPPER:-${MA_AUTOMATOR_CONF_UPPER:-3.6}}"
ANCHOR="${ANCHOR:-00_core_modern}"
# Tempo lane defaults for tempo_norms sidecar
export TEMPO_LANE_ID="${TEMPO_LANE_ID:-tier1__2015_2024}"
export TEMPO_BIN_WIDTH="${TEMPO_BIN_WIDTH:-2.0}"
export TEMPO_DB="${TEMPO_DB:-}"
# Ensure historical echo DB path is always correct, even if MA_DATA_ROOT points to repo root.
export HISTORICAL_ECHO_DB="${HISTORICAL_ECHO_DB:-$REPO/data/private/local_assets/historical_echo/historical_echo.db}"
# Key lane defaults for key_norms sidecar (bind after HISTORICAL_ECHO_DB is set)
export KEY_LANE_ID="${KEY_LANE_ID:-$TEMPO_LANE_ID}"
export KEY_DB="${KEY_DB:-$HISTORICAL_ECHO_DB}"
# Prefer project namespace entrypoint; fall back to legacy script if needed.
# SIDE_PY is the python we force for sidecar (default: repo venv, else PY_BIN).
SIDE_PY="${SIDE_PY:-$PY_BIN}"
if [[ -x "$REPO/.venv/bin/python" ]]; then
PIPELINE_DRIVER="${PIPELINE_DRIVER:-$REPO/.venv/bin/python -m ma_audio_engine.tools.pipeline_driver}"
SIDE_PY="${SIDE_PY:-$REPO/.venv/bin/python}"
else
  PIPELINE_DRIVER="${PIPELINE_DRIVER:-$PY_BIN -m ma_audio_engine.tools.pipeline_driver}"
fi

# Align pipeline base to the repo data folder for Automator runs.
export MA_DATA_ROOT="${MA_DATA_ROOT:-$REPO/data}"
# Ensure repo modules are importable for helper scripts
export PYTHONPATH="${PYTHONPATH:-}:$REPO:$REPO/engines/audio_engine/src:$REPO/engines/lyrics_engine/src:$REPO/src"
# Default sidecar command (templated)
DEFAULT_SIDECAR_CMD="$SIDE_PY tools/tempo_sidecar_runner.py --audio {audio} --out {out}"
export MA_TEMPO_SIDECAR_CMD="${MA_TEMPO_SIDECAR_CMD:-$DEFAULT_SIDECAR_CMD}"
OUT_ROOT="$REPO/data/features_output"
success_count=0
failure_count=0
# Optional: tee Automator #1 logs if AUTOMATOR_LOG is set
if [[ -n "${AUTOMATOR_LOG:-}" ]]; then
  exec > >(tee -a "$AUTOMATOR_LOG") 2>&1
  echo "[INFO] Drag-and-drop Automator logging to $AUTOMATOR_LOG"
fi

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERR] Required tool '$1' not found on PATH." >&2
    exit 1
  fi
}

# These are mostly sanity checks; the extractor itself uses Python + libs.
need ffprobe
need jq

if [[ ! -x "$PY_BIN" ]]; then
  echo "[ERR] Python venv not found or not executable: $PY_BIN" >&2
  exit 1
fi

# Ensure repo root + src + project src on PYTHONPATH so adapters/sitecustomize and project modules are available.
export PYTHONPATH="$REPO:$REPO/src:$REPO/tools:$REPO/engines/audio_engine/src:$REPO/engines/lyrics_engine/src:$REPO/engines/ttc_engine/src:$REPO/hosts/advisor_host_core/src:${PYTHONPATH:-}"
# Optional: sidecar dependency preflight using repo venv
if [[ -x "$REPO/infra/scripts/check_sidecar_deps.sh" ]]; then
  PY_BIN="$PY_BIN" "$REPO/infra/scripts/check_sidecar_deps.sh" || exit 1
fi
# Ensure we run commands from the repo root so relative paths (schemas, etc.) resolve.
cd "$REPO"

# Enforce pinned deps to avoid runtime version drift (warn and exit if mismatched).
if ! "$PY_BIN" - <<'PY' 2>/dev/null; then
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

# Optional: fast dependency preflight for sidecar
if [[ -x "$REPO/infra/scripts/check_sidecar_deps.sh" ]]; then
  PY_BIN="$PY_BIN" "$REPO/infra/scripts/check_sidecar_deps.sh" || exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "[ERR] Drag & drop one or more audio files onto this workflow." >&2
  exit 1
fi

FAIL_ON_CLIP_DBFS="${FAIL_ON_CLIP_DBFS:-}"

yyyy="$(date +%Y)"
mm="$(date +%m)"
dd="$(date +%d)"
CLIP_ARGS=()

for IN_PATH in "$@"; do
  if [[ ! -f "$IN_PATH" ]]; then
    echo "[WARN] Skipping non-file: $IN_PATH"
    continue
  fi

  base="$(basename "$IN_PATH")"
  stem="${base%.*}"
  ts="$(date -u +%Y%m%d_%H%M%S)"

  # Use day bucket to mirror legacy layout: features_output/YYYY/MM/DD/<stem>
 OUT_DIR="$OUT_ROOT/$yyyy/$mm/$dd/$stem"
  mkdir -p "$OUT_DIR"
  rm -f "$OUT_DIR"/* 2>/dev/null || true

  echo "== Automator :: $stem @ $ts =="
 echo "→ Dropped path: $IN_PATH"
 echo "→ Output folder: $OUT_DIR"
 stage_start "automator_track" stem="$stem" out_dir="$OUT_DIR"

  # Unified pipeline driver; use hci-only to mirror legacy Automator #2 outputs
  MODE="hci-only"
  echo "[pipeline] driver ($MODE)"
  TS="$(date -u +%Y%m%d_%H%M%S)"
  FEATURES_JSON="$OUT_DIR/${stem}_${TS}.features.json"
  # Sidecar path stays stable (matches pipeline_driver default) so downstream tools can locate it.
  SIDECAR_JSON="$OUT_DIR/${stem}.sidecar.json"
  MERGED_JSON="$OUT_DIR/${stem}_${TS}.merged.json"
  HCI_JSON="$OUT_DIR/${stem}_${TS}.hci.json"
  TTC_JSON="$OUT_DIR/${stem}_${TS}.ttc.json"
  CLIENT_TXT="$OUT_DIR/$stem.client.txt"
  CLIENT_JSON="$OUT_DIR/$stem.client.json"
  CLIENT_RICH_TXT="$OUT_DIR/$stem.client.rich.txt"
  NEIGHBORS_JSON="$OUT_DIR/$stem.neighbors.json"
  TEMPO_NORMS_JSON="$OUT_DIR/$stem.tempo_norms.json"
  KEY_NORMS_JSON="$OUT_DIR/$stem.key_norms.json"

  # Extract features + sidecar
  MA_TEMPO_SIDECAR_CMD="$MA_TEMPO_SIDECAR_CMD" \
  PYTHONPATH="$PYTHONPATH" \
  "$SIDE_PY" "$REPO/.venv/bin/ma-audio-features" \
    --audio "$IN_PATH" \
    --out "$FEATURES_JSON" \
    --tempo-sidecar-json-out "$SIDECAR_JSON" \
    --tempo-backend sidecar || true
  # Ensure sidecar exists even if the extractor fell back
  if [[ ! -f "$SIDECAR_JSON" ]]; then
    PYTHONPATH="$PYTHONPATH" "$SIDE_PY" tools/tempo_sidecar_runner.py \
      --audio "$IN_PATH" \
      --out "$SIDECAR_JSON" || true
  fi

  # Merge
  if [[ -f "$FEATURES_JSON" ]]; then
    MA_TEMPO_SIDECAR_CMD="$MA_TEMPO_SIDECAR_CMD" \
    PYTHONPATH="$PYTHONPATH" \
    "$SIDE_PY" "$REPO/.venv/bin/equilibrium-merge" \
      --internal "$FEATURES_JSON" \
      --out "$MERGED_JSON" || true
  fi

  # TTC estimate
  PYTHONPATH="$PYTHONPATH" "$SIDE_PY" tools/ttc_auto_estimate.py \
    --audio "$IN_PATH" \
    --out "$TTC_JSON" || true

  # HCI from features
  if [[ -f "$FEATURES_JSON" ]]; then
    PYTHONPATH="$PYTHONPATH" "$SIDE_PY" tools/ma_simple_hci_from_features.py \
      --features "$FEATURES_JSON" \
      --out "$HCI_JSON" || true
  fi

  # Tempo norms sidecar (uses merged tempo BPM)
  if [[ -f "$MERGED_JSON" ]]; then
    tempo_bpm="$(
      python3 - <<'PY' "$MERGED_JSON"
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    bpm = data.get("tempo_bpm") or data.get("tempo_primary")
    if bpm is not None:
        print(f"{float(bpm):.6f}")
except Exception:
    pass
PY
    )"
    if [[ -n "$tempo_bpm" ]]; then
      db_path="${TEMPO_DB}"
      if [[ -z "$db_path" || ! -f "$db_path" ]]; then
        db_path="$REPO/data/private/local_assets/lyric_intel/tempo_demo.db"
      fi
      PYTHONPATH="$PYTHONPATH" "$SIDE_PY" - <<'PY' "$REPO" "$stem" "$TEMPO_LANE_ID" "$tempo_bpm" "$db_path" "$TEMPO_NORMS_JSON"
import sys, pathlib
repo, song_id, lane_id, tempo_bpm, db_path, out_path = sys.argv[1:]
sys.path.insert(0, str(pathlib.Path(repo)))
from tools import tempo_norms_sidecar as mod  # type: ignore
sys.argv = [
    "tempo_norms_sidecar.py",
    "--song-id", song_id,
    "--lane-id", lane_id,
    "--song-bpm", tempo_bpm,
    "--db", db_path,
    "--out", out_path,
    "--overwrite",
]
mod.main()
PY
    fi
  fi

  # Key norms sidecar (best effort)
  if [[ -f "$MERGED_JSON" ]]; then
    song_key_mode="$(
      python3 - <<'PY' "$MERGED_JSON"
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    key = data.get("key")
    mode = data.get("mode")
    if key and mode:
        print(f"{key} {mode}")
except Exception:
    pass
PY
    )"
    if [[ -n "$song_key_mode" ]]; then
      db_path="${KEY_DB}"
      if [[ -z "$db_path" || ! -f "$db_path" ]]; then
        db_path="$HISTORICAL_ECHO_DB"
      fi
      PYTHONPATH="$PYTHONPATH" "$SIDE_PY" - <<'PY' "$REPO" "$stem" "$KEY_LANE_ID" "$song_key_mode" "$db_path" "$KEY_NORMS_JSON"
import sys, pathlib
repo, song_id, lane_id, song_key, db_path, out_path = sys.argv[1:]
sys.path.insert(0, str(pathlib.Path(repo)))
from tools import key_norms_sidecar as mod  # type: ignore
argv = [
    "key_norms_sidecar.py",
    "--song-id", song_id,
    "--lane-id", lane_id,
    "--db", db_path,
    "--out", out_path,
    "--overwrite",
]
if song_key:
    argv += ["--song-key", song_key]
sys.argv = argv
mod.main()
PY
    fi
  fi

  # Pack + client helpers (rich), then copy to plain names
  if [[ -f "$MERGED_JSON" ]]; then
    $SIDE_PY -m tools.pack_writer \
      --merged "$MERGED_JSON" \
      --features "$FEATURES_JSON" \
      --out-dir "$OUT_DIR" \
      --anchor "$ANCHOR" \
      --client-txt "$CLIENT_RICH_TXT" \
      --client-json "$CLIENT_JSON" || true
    cp -f "$CLIENT_RICH_TXT" "$CLIENT_TXT" 2>/dev/null || true

    # Inject echo + neighbors
    PYTHONPATH="$PYTHONPATH" "$SIDE_PY" tools/hci/ma_add_echo_to_client_rich_v1.py \
      --root "$OUT_DIR" \
      --year-max 2025 || true
    found_neigh=$(find "$OUT_DIR" -maxdepth 1 -name "*.neighbors.json" | head -n1 || true)
    if [[ -n "$found_neigh" ]]; then
      mv "$found_neigh" "$NEIGHBORS_JSON" 2>/dev/null || true
    fi
    # Append audio metadata probe (places block before AUDIO_PIPELINE)
    PYTHONPATH="$PYTHONPATH" "$SIDE_PY" tools/append_metadata_to_client_rich.py \
      --track-dir "$OUT_DIR" || true
    # Inject tempo overlay from sidecar (once, with logging)
    if [[ -f "$OUT_DIR/$stem.tempo_norms.json" && -f "$CLIENT_RICH_TXT" ]]; then
      echo "[tempo_overlay] injecting tempo block into $CLIENT_RICH_TXT"
      if PYTHONPATH="$PYTHONPATH" "$SIDE_PY" tools/ma_add_tempo_overlay_to_client_rich.py --client-rich "$CLIENT_RICH_TXT"; then
        echo "[tempo_overlay] injected OK"
      else
        echo "[tempo_overlay] inject failed"
      fi
    else
      echo "[tempo_overlay] skipped (missing sidecar or client rich)"
    fi
    # Inject key overlay from sidecar
    if [[ -f "$KEY_NORMS_JSON" && -f "$CLIENT_RICH_TXT" ]]; then
      echo "[key_overlay] injecting key block into $CLIENT_RICH_TXT"
      if PYTHONPATH="$PYTHONPATH" "$SIDE_PY" tools/ma_add_key_overlay_to_client_rich.py --client-rich "$CLIENT_RICH_TXT"; then
        echo "[key_overlay] injected OK"
      else
        echo "[key_overlay] inject failed"
      fi
    else
      echo "[key_overlay] skipped (missing sidecar or client rich)"
    fi
    # Prune extras not part of the 10-file payload
    find "$OUT_DIR" -maxdepth 1 -name "*.client.rich.json" -delete 2>/dev/null || true
    find "$OUT_DIR" -maxdepth 1 -name "*.pack.json" -delete 2>/dev/null || true
  fi

  # Run summary for quick inspection
  RUN_SUMMARY="$OUT_DIR/run_summary.json"
  $SIDE_PY - <<'PY' "$OUT_DIR" "$stem" "$FEATURES_JSON" "$SIDECAR_JSON" "$MERGED_JSON" "$HCI_JSON" "$TTC_JSON" "$CLIENT_TXT" "$CLIENT_JSON" "$CLIENT_RICH_TXT" "$NEIGHBORS_JSON" "$TEMPO_NORMS_JSON" "$KEY_NORMS_JSON"
import json, sys, os, time
args = sys.argv[1:]
labels = [
    "out_dir",
    "stem",
    "features",
    "sidecar",
    "merged",
    "hci",
    "ttc",
    "client_txt",
    "client_json",
    "client_rich_txt",
    "neighbors",
    "tempo_norms",
    "key_norms",
]
data = dict(zip(labels, args))
artifacts = {}
def add(name, path):
    if path and os.path.isfile(path):
        artifacts[name] = {
            "path": path,
            "bytes": os.path.getsize(path),
        }
for label in labels[2:]:
    add(label, data.get(label, ""))
summary = {
    "out_dir": data.get("out_dir", ""),
    "stem": data.get("stem", ""),
    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "artifacts": artifacts,
    "warnings": [],
}
with open(os.path.join(data.get("out_dir","."), "run_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
PY

  # Prune older timestamped artifacts to keep the latest set
  for kind in features merged hci ttc; do
    latest="$OUT_DIR/${stem}_${TS}.${kind}.json"
    for f in "$OUT_DIR"/"${stem}"_*."${kind}.json"; do
      if [[ "$f" != "$latest" ]]; then
        rm -f "$f" 2>/dev/null || true
      fi
    done
  done
  # Remove stale non-timestamped artifacts we don't ship
  rm -f "$OUT_DIR/$stem.features.json" "$OUT_DIR/$stem.merged.json" 2>/dev/null || true

  stage_end "automator_track" status="ok" out_dir="$OUT_DIR"
  success_count=$((success_count+1))
done

echo "[OK] Drag-and-drop Automator complete."
echo "[SUMMARY] success=$success_count failure=$failure_count"
