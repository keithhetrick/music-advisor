#!/usr/bin/env python3
"""
Trace helper:
- Prints LUFS for the dropped path and its normalized counterpart (if any)
- Auto-selects the best candidate (prefers audio_norm within ±tol of target)
- Emits a single JSON object describing both and the chosen input
"""

from __future__ import annotations
import argparse, json, sys, hashlib
from pathlib import Path

ANCHORS = [
    "00_core_modern",
    "01_echo_1985_89",
    "02_echo_1990_94",
    "03_echo_1995_99",
    "04_echo_2000_04",
    "05_echo_2005_09",
    "06_echo_2010_14",
    "07_echo_2015_19",
    "08_indie_singer_songwriter",
    "09_latin_crossover_eval",
    "10_negatives_main_eval",
    "11_negatives_canonical_eval",
    "12_negatives_novelty_eval",
    "99_legacy_pop_eval",
]

def sha1(path: Path) -> str | None:
    if not path.exists(): return None
    h=hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def read_audio(path: Path):
    try:
        import soundfile as sf
        y, sr = sf.read(str(path), always_2d=False)
        import numpy as np
        if getattr(y, "ndim", 1) > 1:
            y = y.mean(axis=1)
        y = y.astype("float32", copy=False)
        return y, sr
    except Exception:
        import librosa
        y, sr = librosa.load(str(path), sr=None, mono=True)
        import numpy as np
        return y.astype("float32", copy=False), sr

def lufs_r128(y, sr) -> float:
    import pyloudnorm as pyln
    return float(pyln.Meter(sr).integrated_loudness(y))

def measure(path: Path) -> dict:
    out = {"path": str(path), "exists": path.exists()}
    if path.exists():
        out["sha1"] = sha1(path)
        try:
            y, sr = read_audio(path)
            out["lufs_r128"] = lufs_r128(y, sr)
        except Exception as e:
            out["error"] = f"{type(e).__name__}: {e}"
    return out

def counterpart(path: Path, calib_root: Path | None) -> Path | None:
    s = str(path)
    if "/audio_norm/" in s:
        # Provide the /audio/ counterpart
        return Path(s.replace("/audio_norm/", "/audio/"))
    if "/audio/" in s:
        cand = Path(s.replace("/audio/", "/audio_norm/"))
        if cand.exists(): return cand
    if calib_root:
        # Try rebuild via anchors
        for a in ANCHORS:
            token = f"/{a}/"
            if token in s:
                suffix = s.split(token, 1)[1]
                cand = calib_root / "audio_norm" / a / suffix
                if cand.exists(): return cand
    return None

def choose(a: dict, b: dict | None, target: float, tol: float, prefer_norm: bool) -> dict:
    """
    a = original, b = normalized (if exists). Choose:
      - if b exists and |b - target| <= tol → choose b
      - elif a exists and |a - target| <= tol → choose a
      - else choose the one closer to target; mark as out_of_tolerance
    """
    def dist(x): return abs((x or 1e9) - target)
    out = {"chosen": None, "reason": "", "out_of_tolerance": False}
    a_l = a.get("lufs_r128")
    b_l = b.get("lufs_r128") if b else None

    if b and b.get("exists") and b_l is not None and abs(b_l - target) <= tol:
        out["chosen"], out["reason"] = b, "normalized_within_tolerance"
        return out
    if a.get("exists") and a_l is not None and abs(a_l - target) <= tol:
        out["chosen"], out["reason"] = a, "original_within_tolerance"
        return out

    if b and b.get("exists") and b_l is not None:
        if a_l is None or dist(b_l) <= dist(a_l):
            out["chosen"], out["reason"], out["out_of_tolerance"] = b, "normalized_closest", True
            return out
    if a.get("exists") and a_l is not None:
        out["chosen"], out["reason"], out["out_of_tolerance"] = a, "original_closest", True
        return out

    out["reason"] = "no_readable_candidates"
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--calib-root", default=None)
    ap.add_argument("--prefer-norm", default="1")
    ap.add_argument("--target", type=float, default=-10.0)
    ap.add_argument("--tol", type=float, default=0.8)
    args = ap.parse_args()

    p = Path(args.path)
    calib_root = Path(args.calib_root) if args.calib_root else None
    prefer_norm = (str(args.prefer_norm) == "1")

    original = measure(p)
    norm_p = counterpart(p, calib_root) if prefer_norm else None
    normalized = measure(norm_p) if norm_p else None

    choice = choose(original, normalized, args.target, args.tol, prefer_norm=True)
    out = {
        "original": original,
        "normalized": normalized,
        "chosen": choice.get("chosen"),
        "choice_reason": choice.get("reason"),
        "out_of_tolerance": choice.get("out_of_tolerance"),
        "target": args.target,
        "tol": args.tol,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
