#!/usr/bin/env bash
# tools/loudnorm_exact.sh
# Exact(-ish) two-pass EBU R128 normalization with gentle pre-compression.
# Usage: bash tools/loudnorm_exact.sh <in.wav> <out.wav> [I=-10] [TP=-1] [LRA=11]

set -euo pipefail

IN="${1:-}"; OUT="${2:-}"
I_TGT="${3:--10}"; TP_TGT="${4:--1}"; LRA_TGT="${5:-11}"

if [[ -z "${IN}" || -z "${OUT}" ]]; then
  echo "usage: $0 <in.wav> <out.wav> [I=-10] [TP=-1] [LRA=11]" >&2
  exit 64
fi

command -v ffmpeg >/dev/null || { echo "[loudnorm] ffmpeg not found"; exit 127; }
command -v jq     >/dev/null || { echo "[loudnorm] jq not found"; exit 127; }
[[ -f "$IN" ]] || { echo "[loudnorm] input not found: $IN"; exit 66; }
mkdir -p "$(dirname "$OUT")"

TMP_JSON="$(mktemp -t loudnorm_stats.XXXXXX.json)"
cleanup() { rm -f "$TMP_JSON"; }
trap cleanup EXIT
ffmpeg -hide_banner -nostats -y -i "$IN" \
  -af loudnorm=I=${I_TGT}:TP=${TP_TGT}:LRA=${LRA_TGT}:print_format=json \
  -f null - 2> >(awk 'BEGIN{p=0} /^\s*{/{p=1} {if(p)print} /^\s*}/{if(p){exit}}' > "$TMP_JSON")

mi=$(jq -r '.input_i'      "$TMP_JSON")
mtp=$(jq -r '.input_tp'    "$TMP_JSON")
mlra=$(jq -r '.input_lra'  "$TMP_JSON")
mth=$(jq -r '.input_thresh' "$TMP_JSON")     # <-- fixed space
off=$(jq -r '.target_offset' "$TMP_JSON")    # <-- fixed space

if [[ -z "$mi" || -z "$mtp" || -z "$mlra" || -z "$mth" || -z "$off" || "$mi" == "null" ]]; then
  echo "[loudnorm] failed to parse pass-1 JSON; see $TMP_JSON" >&2
  cat "$TMP_JSON" >&2 || true
  rm -f "$TMP_JSON"
  exit 2
fi

ffmpeg -hide_banner -nostats -y -i "$IN" \
  -af "acompressor=threshold=-16dB:ratio=3:attack=5:release=80:makeup=5,\
loudnorm=I=${I_TGT}:TP=${TP_TGT}:LRA=${LRA_TGT}:measured_I=${mi}:measured_TP=${mtp}:measured_LRA=${mlra}:measured_thresh=${mth}:offset=${off}:linear=false:print_format=summary" \
  -ar 44100 -c:a pcm_f32le "$OUT"

rm -f "$TMP_JSON"

python - "$OUT" "$I_TGT" <<'PY' || true
import sys
try:
    import soundfile as sf, pyloudnorm as pyln, numpy as np
except Exception:
    print("[verify] skip (pyloudnorm/soundfile not available)")
    sys.exit(0)
p=sys.argv[1]; target=sys.argv[2]
y,sr=sf.read(p, always_2d=False)
if getattr(y, "ndim", 1) > 1: y = y.mean(axis=1)
l=float(pyln.Meter(sr).integrated_loudness(y))
print(f"[verify] {p} → {l:.2f} LUFS (target {target} LUFS)")
PY
