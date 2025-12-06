#!/usr/bin/env python3
# Measure EBU R128 integrated loudness and write it into features JSON (no audio change).

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def read_audio(path: Path):
    # Prefer soundfile; fallback to librosa
    try:
        import soundfile as sf, numpy as np
        y, sr = sf.read(str(path), always_2d=False)
        if getattr(y, "ndim", 1) > 1:
            y = y.mean(axis=1)
        y = y.astype("float32", copy=False)
        return y, sr
    except Exception:
        import librosa
        y, sr = librosa.load(str(path), sr=None, mono=True)
        return y.astype("float32", copy=False), sr

def measure_lufs_r128(y, sr):
    import pyloudnorm as pyln
    meter = pyln.Meter(sr)  # EBU R128
    return float(meter.integrated_loudness(y))

def lin_to_db(lin: float) -> float:
    import math
    if lin <= 1e-12: return -120.0
    return 20.0 * math.log10(lin)

def measure_sample_peak_dbfs(y) -> float:
    import numpy as np
    pk = float(abs(y).max()) if y.size else 0.0
    return lin_to_db(pk)

def main():
    ap = argparse.ArgumentParser(description="Postprocess features with R128 loudness.")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--features", required=True)
    args = ap.parse_args()

    feats_p = Path(args.features)
    if not feats_p.exists():
        print(f"[r128] features not found: {feats_p}", file=sys.stderr)
        sys.exit(2)

    # Load JSON
    d = json.loads(feats_p.read_text())
    ff = d.get("features_full") or {}
    d.setdefault("features_full", ff)

    # Read + measure
    y, sr = read_audio(Path(args.audio))
    lufs = measure_lufs_r128(y, sr)
    peak_dbfs = measure_sample_peak_dbfs(y)

    # Preserve legacy if present
    if "loudness_lufs_legacy" not in ff and "loudness_lufs" in ff:
        ff["loudness_lufs_legacy"] = float(ff["loudness_lufs"])

    # Write canonical fields used downstream
    ff["loudness_lufs_r128"] = float(lufs)
    ff["loudness_lufs"] = float(lufs)  # axes consume this
    ff["sample_peak_dbfs"] = float(peak_dbfs)

    # Mirror shallow features if present
    if isinstance(d.get("features"), dict):
        d["features"]["loudness_lufs"] = float(lufs)

    feats_p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    print(f"[r128] features updated: LUFS_r128={lufs:.2f}  peak={peak_dbfs:.2f} dBFS  → {feats_p}")

if __name__ == "__main__":
    main()
