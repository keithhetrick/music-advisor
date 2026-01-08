#!/usr/bin/env python3
"""
Lightweight TTC auto-estimator for unlabeled audio.

Strategy v1 (heuristic):
- Load mono audio (librosa).
- Build chroma-based self-similarity matrix to detect repeated structure.
- Score time offsets by recurrence density; choose the earliest high-density peak as chorus guess.
- Convert to bars if BPM is provided or can be estimated.

Outputs JSON with:
  {
    "ttc_seconds_first_chorus": <float|null>,
    "ttc_bars_first_chorus": <float|null>,
    "source": "Auto",
    "estimation_method": "ttc_auto_v1",
    "bpm_used": <float|null>
  }
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import librosa
    import numpy as np
except Exception:  # noqa: BLE001
    librosa = None
    np = None

DEFAULT_SR = 22050
HOP = 512


def _load_audio(path: Path, sr: int) -> Tuple[Optional[Any], Optional[int]]:
    import sys
    if librosa is None:
        print(f"[ttc_auto_estimate] ERROR: librosa not available", file=sys.stderr)
        return None, None
    try:
        y, sr_out = librosa.load(path, sr=sr, mono=True)
        print(f"[ttc_auto_estimate] DEBUG: librosa.load returned y={type(y).__name__ if y is not None else 'None'}, len={len(y) if y is not None else 'N/A'}, sr={sr_out}", file=sys.stderr)
        if y is None or len(y) == 0:
            print(f"[ttc_auto_estimate] ERROR: loaded audio is empty: {path}", file=sys.stderr)
            return None, None
        print(f"[ttc_auto_estimate] DEBUG: audio loaded successfully, shape={y.shape if hasattr(y, 'shape') else 'N/A'}", file=sys.stderr)
        return y, sr_out
    except Exception as e:
        print(f"[ttc_auto_estimate] ERROR: failed to load audio {path}: {type(e).__name__}: {e}", file=sys.stderr)
        return None, None


def _estimate_bpm(y, sr: int, bpm_hint: Optional[float]) -> Tuple[Optional[float], Optional[Any]]:
    if librosa is None or np is None:
        return bpm_hint, None
    if bpm_hint:
        return bpm_hint, None
    try:
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP)
        tempo = float(tempo) if tempo is not None else None
        return tempo, beats
    except Exception:
        return bpm_hint, None


def _pick_ttc(y, sr: int) -> Optional[float]:
    if librosa is None or np is None:
        return None
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP)
        rec = librosa.segment.recurrence_matrix(chroma, mode="affinity", sym=True)
        # Blur diagonals to emphasize repeated blocks.
        rec_filt = librosa.segment.timelag_filter(rec, axis=-1)
        strength = rec_filt.sum(axis=0)
        if np.max(strength) <= 0:
            return None
        peak = int(np.argmax(strength))
        ttc_seconds = float(librosa.frames_to_time(peak, sr=sr, hop_length=HOP))
        return max(0.0, ttc_seconds)
    except Exception:
        return None


def estimate_ttc(audio_path: Path, bpm_hint: Optional[float] = None, sr: int = DEFAULT_SR) -> Dict[str, Optional[float]]:
    import sys
    print(f"[ttc_auto_estimate] attempting to load: {audio_path} (exists={audio_path.exists()})", file=sys.stderr)
    y, sr_loaded = _load_audio(audio_path, sr)
    if y is None or sr_loaded is None:
        print(f"[ttc_auto_estimate] audio load failed, returning status=audio_load_failed", file=sys.stderr)
        return {
            "ttc_seconds_first_chorus": None,
            "ttc_bars_first_chorus": None,
            "source": "Auto",
            "ttc_source": "Auto",
            "estimation_method": "ttc_auto_v1",
            "ttc_estimation_method": "ttc_auto_v1",
            "bpm_used": bpm_hint,
            "status": "audio_load_failed",
        }
    bpm_used, beats = _estimate_bpm(y, sr_loaded, bpm_hint)
    ttc_seconds = _pick_ttc(y, sr_loaded)
    bars = None
    if ttc_seconds is not None and bpm_used:
        beats_per_sec = bpm_used / 60.0
        bars = (ttc_seconds * beats_per_sec) / 4.0
    return {
        "ttc_seconds_first_chorus": ttc_seconds,
        "ttc_bars_first_chorus": bars,
        "source": "Auto",
        "ttc_source": "Auto",
        "estimation_method": "ttc_auto_v1",
        "ttc_estimation_method": "ttc_auto_v1",
        "bpm_used": bpm_used,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Auto-estimate TTC for an audio file.")
    ap.add_argument("--audio", required=True, help="Path to audio file.")
    ap.add_argument("--out", required=True, help="Output JSON path.")
    ap.add_argument("--bpm", type=float, default=None, help="Optional BPM hint to convert seconds->bars.")
    ap.add_argument("--sr", type=int, default=DEFAULT_SR, help="Sample rate for loading audio.")
    ap.add_argument("--title", help="Optional title for metadata.")
    ap.add_argument("--artist", help="Optional artist for metadata.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    audio_path = Path(args.audio).expanduser()
    if not audio_path.exists():
        raise SystemExit(f"Audio not found: {audio_path}")
    result = estimate_ttc(audio_path, bpm_hint=args.bpm, sr=args.sr)
    if args.title:
        result["title"] = args.title
    if args.artist:
        result["artist"] = args.artist
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[ttc_auto_estimate] wrote {out_path}")


if __name__ == "__main__":
    main()
