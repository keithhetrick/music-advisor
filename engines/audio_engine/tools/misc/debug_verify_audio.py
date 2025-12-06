#!/usr/bin/env python3
# Print LUFS (R128), sample peak dBFS, duration, SR, channels, and sha1 for a given file.

from __future__ import annotations
import argparse, hashlib, sys
from pathlib import Path

def sha1(path: Path) -> str:
    h=hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def read_audio(path: Path):
    try:
        import soundfile as sf, numpy as np
        y, sr = sf.read(str(path), always_2d=True)
        return y.astype("float32"), sr, y.shape[1]
    except Exception:
        import librosa, numpy as np
        y, sr = librosa.load(str(path), sr=None, mono=False)
        if y.ndim == 1: y = y[None, :]
        y = y.T.astype("float32")
        return y, sr, y.shape[1]

def to_mono(y):
    import numpy as np
    if y.ndim == 1: return y
    return y.mean(axis=1).astype("float32")

def lufs_r128(y, sr):
    import pyloudnorm as pyln
    return float(pyln.Meter(sr).integrated_loudness(y))

def peak_dbfs(y):
    import numpy as np, math
    pk=float(abs(y).max()) if y.size else 0.0
    if pk<=1e-12: return -120.0
    return 20.0*math.log10(pk)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("path")
    args=ap.parse_args()
    p=Path(args.path)
    y,sr,ch=read_audio(p)
    mono=to_mono(y)
    import numpy as np
    print(f"path: {p}")
    print(f"sha1: {sha1(p)}")
    print(f"sr: {sr}  channels: {ch}  duration_sec: {y.shape[0]/sr:.2f}")
    print(f"peak_dbfs(sample): {peak_dbfs(mono):.2f}")
    try:
        print(f"loudness_lufs_r128: {lufs_r128(mono, sr):.2f}")
    except Exception as e:
        print(f"loudness_lufs_r128: ERROR ({e})")
        sys.exit(2)

if __name__=="__main__":
    main()
