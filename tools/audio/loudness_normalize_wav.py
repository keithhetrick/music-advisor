#!/usr/bin/env python3
# tools/loudness_normalize_wav.py
# Normalize a WAV's integrated loudness to a target (EBU R128), with peak ceiling.
from __future__ import annotations
import argparse, sys
from pathlib import Path

def read_audio(path):
    import soundfile as sf, numpy as np
    y, sr = sf.read(str(path), always_2d=True)
    y = y.astype("float32", copy=False)  # shape: (N, C)
    return y, sr

def to_mono(y):
    import numpy as np
    if y.ndim == 1: return y
    return y.mean(axis=1).astype("float32", copy=False)

def measure_lufs_r128(y, sr):
    import pyloudnorm as pyln
    meter = pyln.Meter(sr)  # EBU R128
    return float(meter.integrated_loudness(y))

def db_to_lin(db): 
    import math
    return 10.0 ** (db / 20.0)

def lin_to_db(lin):
    import math
    if lin <= 1e-12: return -120.0
    return 20.0 * math.log10(lin)

def apply_gain(y, gain_lin):
    import numpy as np
    return (y * gain_lin).astype("float32", copy=False)

def peak_linear(y):
    import numpy as np
    return float(abs(y).max()) if y.size else 0.0

def write_audio(path, y, sr, subtype=None):
    import soundfile as sf
    # Write float32 WAV to preserve headroom unless subtype specified.
    sf.write(str(path), y, sr, subtype=subtype or "PCM_16")

def main():
    ap = argparse.ArgumentParser(description="Normalize WAV loudness to target LUFS with peak ceiling.")
    ap.add_argument("--in", dest="inp", required=True, help="Input WAV")
    ap.add_argument("--out", dest="out", required=True, help="Output WAV")
    ap.add_argument("--target", type=float, default=-12.0, help="Target LUFS (default: -12)")
    ap.add_argument("--tp-ceiling", type=float, default=-1.0, help="Peak ceiling in dBFS (approx, default: -1 dBFS)")
    ap.add_argument("--pcm16", action="store_true", help="Write PCM_16 (default). If not set, writes PCM_16 anyway.")
    args = ap.parse_args()

    inp = Path(args.inp); out = Path(args.out)
    try:
        import numpy as np, soundfile as sf, pyloudnorm as pyln  # ensure deps
    except Exception as e:
        print(f"[normalize] Missing deps: pip install pyloudnorm soundfile numpy ({e})", file=sys.stderr)
        sys.exit(2)

    y, sr = read_audio(inp)              # (N, C)
    y_mono = to_mono(y)                  # (N,)
    lufs_in = measure_lufs_r128(y_mono, sr)

    # Gain to target
    gain_db = args.target - lufs_in
    gain_lin = db_to_lin(gain_db)
    y_gain = apply_gain(y, gain_lin)

    # Peak ceiling protection (approx sample-peak)
    pk = peak_linear(y_gain)
    ceil_lin = db_to_lin(args.tp_ceiling)  # e.g., -1 dBFS -> 0.891
    adj_lin = 1.0
    if pk > ceil_lin and pk > 0.0:
        adj_lin = ceil_lin / pk
        y_gain = apply_gain(y_gain, adj_lin)
        gain_db = lin_to_db(gain_lin * adj_lin)

    # Write
    out.parent.mkdir(parents=True, exist_ok=True)
    write_audio(out, y_gain, sr, subtype="PCM_16" if args.pcm16 else "PCM_16")

    # Verify post LUFS (approx, since peak safety may reduce loudness)
    lufs_out = measure_lufs_r128(to_mono(y_gain), sr)
    print(f"[normalize] {inp.name}  LUFS_in={lufs_in:.2f} → LUFS_out={lufs_out:.2f}  gain={gain_db:+.2f} dB  peak_post={lin_to_db(peak_linear(y_gain)):.2f} dBFS")
    print(f"[normalize] wrote: {out}")

if __name__ == "__main__":
    main()
