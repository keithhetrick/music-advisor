#!/usr/bin/env bash
set -euo pipefail

# ---- PATH so Automator sees Homebrew + python ----
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

# ---- Config ----
AUDIO="$1"
if [[ ! -f "$AUDIO" ]]; then
  echo "[ERR] audio not found: $AUDIO" >&2
  exit 2
fi
BN="$(basename "${AUDIO%.*}")"
TS="$(date +%Y/%m/%d)"
REPO="${REPO:-$HOME/music-advisor}"
OUTROOT="$REPO/features_output/$TS/$BN"
mkdir -p "$OUTROOT"

echo "== Automator run :: $BN.wav @ $(date +%Y%m%d_%H%M%S) =="
echo "→ Dropped path: $AUDIO"
echo "→ Output folder: $OUTROOT"

# ---- LUFS guard (on by default) ----
if [[ "${SKIP_LUFS_GUARD:-0}" == "1" ]]; then
  echo "[r128] LUFS guard: SKIPPED by user."
else
  if command -v python &>/dev/null; then
    python - "$AUDIO" <<'PY'
import sys, soundfile as sf, pyloudnorm as pyln
p=sys.argv[1]; y,sr=sf.read(p)
import numpy as np
if getattr(y,'ndim',1)>1: y=y.mean(axis=1)
lufs = pyln.Meter(sr).integrated_loudness(y)
print(f"[r128] LUFS check: {lufs:.2f} LUFS")
PY
  else
    echo "[WARN] python not found; skipping LUFS check"
  fi
fi

# ---- Stage tool helpers ----
have() { command -v "$1" >/dev/null 2>&1; }
py_file() { [[ -f "$1" ]]; }

# ---- 1) Audio features (optional) -> .features.json ----
FEATURES_JSON="$OUTROOT/${BN}_$(date +%Y%m%d_%H%M%S).features.json"
if py_file "tools/ma_audio_features.py"; then
  python tools/ma_audio_features.py \
    --audio "$AUDIO" \
    --out "$FEATURES_JSON" \
    --cache-dir "$HOME/music-advisor/.ma_cache" \
    --clip-peak-threshold 0.999 \
    --silence-ratio-threshold 0.9 \
    --low-level-dbfs-threshold -40
else
  echo "[ma_audio_features] SKIP (tool not found)"
  exit 1
fi

# ---- 2) R128 enrich (optional) ----
if py_file "tools/r128_update_features.py"; then
  python tools/r128_update_features.py --in "$AUDIO" --features "$FEATURES_JSON" || echo "[r128] enrich failed (continuing)"
else
  echo "[r128] SKIP (tool not found)"
fi

# ---- 3) Beatlink (optional) → .beatlink.json ----
BEAT_JSON="$OUTROOT/${BN}_$(date +%Y%m%d_%H%M%S).beatlink.json"
if py_file "tools/beatlink_builder.py"; then
  python tools/beatlink_builder.py --in "$AUDIO" --out "$BEAT_JSON" || echo "[beatlink] failed (continuing)"
else
  echo "[beatlink] SKIP (tool not found)"
fi

# ---- 4) Lyric ASR (optional) → .lyrics.json ----
LYR_JSON="$OUTROOT/${BN}_$(date +%Y%m%d_%H%M%S).lyrics.json"
if py_file "tools/lyric_asr.py"; then
  python tools/lyric_asr.py --in "$AUDIO" --out "$LYR_JSON" || echo "[lyricflow] failed (continuing)"
else
  echo "[lyricflow] SKIP (tool not found)"
fi

# ---- 5) Lyric axis score (optional) → updates .lyrics.json or separate ----
if py_file "tools/lyric_axis_score.py"; then
  python tools/lyric_axis_score.py --in "$LYR_JSON" --out "$LYR_JSON" || echo "[lyric_intel_engine] failed (continuing)"
else
  echo "[lyric_intel_engine] SKIP (tool not found)"
fi

# ---- 6) Merge internal/external features → .merged.json ----
MERGED_JSON="$OUTROOT/${BN}_$(date +%Y%m%d_%H%M%S).merged.json"
# If you have an external/global feature source, set EXTERNAL here; else leave empty
EXTERNAL=""
if py_file "tools/equilibrium_merge.py"; then
  # ALWAYS pass --internal; pass --external only if file exists
  if [[ -n "$EXTERNAL" && -f "$EXTERNAL" ]]; then
    python tools/equilibrium_merge.py --internal "$FEATURES_JSON" --external "$EXTERNAL" --out "$MERGED_JSON"
  else
    python tools/equilibrium_merge.py --internal "$FEATURES_JSON" --out "$MERGED_JSON"
  fi
else
  echo "[equilibrium_merge] SKIP (tool not found) → copying internal as merged"
  cp "$FEATURES_JSON" "$MERGED_JSON"
fi

# ---- 7) Build pack ----
PACK_JSON="$OUTROOT/${BN}_$(date +%Y%m%d_%H%M%S).pack.json"
python tools/pack_writer.py \
  --audio "$AUDIO" \
  --merged "$MERGED_JSON" \
  ${BEAT_JSON:+--beatlink "$BEAT_JSON"} \
  ${LYR_JSON:+--lyrics "$LYR_JSON"} \
  --out-pack "$PACK_JSON"

echo "✓ Done. Pack: $PACK_JSON"
