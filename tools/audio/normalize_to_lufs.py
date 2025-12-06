#!/usr/bin/env python3
"""
Normalize any WAV to a target integrated LUFS using pyloudnorm (measure) + ffmpeg (apply).
- Writes temp files on the DESTINATION volume to avoid cross-device link errors.
- Uses shutil.move for atomic-ish finalization across filesystems.

Usage:
  python tools/normalize_to_lufs.py \
      --in "/path/in.wav" \
      --out "/path/out.wav" \
      --target -10 \
      --tp -1 \
      --max-iters 2 \
      --tolerance 0.3
"""

from __future__ import annotations
import argparse, math, sys, os, shutil
from pathlib import Path
import soundfile as sf
import numpy as np
import pyloudnorm as pyln
from security import subprocess as sec_subprocess
from security.config import CONFIG as SEC_CONFIG

def sh(cmd: list[str]) -> None:
    p = sec_subprocess.run_safe(
        cmd,
        allow_roots=SEC_CONFIG.allowed_binary_roots,
        timeout=SEC_CONFIG.subprocess_timeout,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\nSTDOUT:\n{p.stdout or ''}\nSTDERR:\n{p.stderr or ''}")

def measure_lufs(path: str) -> float:
    y, sr = sf.read(path, always_2d=True)
    mono = y.mean(axis=1).astype(np.float32)
    meter = pyln.Meter(sr)
    return float(meter.integrated_loudness(mono))

def apply_gain_limit(src: str, dst: str, gain_db: float, tp_db: float) -> None:
    af = f"volume={gain_db}dB,alimiter=limit={tp_db}dB"
    sh(["ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-i", src,
        "-af", af,
        "-c:a", "pcm_f32le",
        dst])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--target", type=float, default=-10.0)
    ap.add_argument("--tp", type=float, default=-1.0)
    ap.add_argument("--max-iters", type=int, default=2)
    ap.add_argument("--tolerance", type=float, default=0.3)
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    # temp files ON DESTINATION VOLUME
    tmp_dir = dst.parent / ".norm_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cur_path = str(src)

    # Pass 1: measure source
    L_in = measure_lufs(cur_path)
    needed_db = args.target - L_in

    # Apply gain + limiter
    tmp1 = str(tmp_dir / "pass1.wav")
    apply_gain_limit(cur_path, tmp1, needed_db, args.tp)
    L_out = measure_lufs(tmp1)

    iters = 1
    cur_path = tmp1
    while iters < args.max_iters and abs(L_out - args.target) > args.tolerance:
        delta_db = args.target - L_out
        tmpn = str(tmp_dir / f"pass{iters+1}.wav")
        apply_gain_limit(cur_path, tmpn, delta_db, args.tp)
        L_out = measure_lufs(tmpn)
        cur_path = tmpn
        iters += 1

    # Move final to destination (same filesystem), then clean tmp
    shutil.move(cur_path, str(dst))
    try:
        # Best-effort cleanup
        for p in tmp_dir.iterdir():
            p.unlink(missing_ok=True)
        tmp_dir.rmdir()
    except Exception:
        pass

    final_lufs = measure_lufs(str(dst))
    print(f"OK: {dst}  LUFS≈{final_lufs:.2f}")

if __name__ == "__main__":
    main()
