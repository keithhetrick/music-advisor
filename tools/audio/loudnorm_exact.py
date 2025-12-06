#!/usr/bin/env python3
"""
Two-pass EBU R128 normalization to an EXACT target using ffmpeg loudnorm.

Usage:
  python tools/loudnorm_exact.py \
      --in "/path/in.wav" \
      --out "/path/out.wav" \
      --target -10 \
      --tp -1 \
      --lra 11
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from security import subprocess as sec_subprocess
from security.config import CONFIG as SEC_CONFIG

def run(cmd: list[str]) -> tuple[int, str, str]:
    p = sec_subprocess.run_safe(
        cmd,
        allow_roots=SEC_CONFIG.allowed_binary_roots,
        timeout=SEC_CONFIG.subprocess_timeout,
        check=False,
    )
    # run_safe raises on disallowed binary; it returns even if rc!=0 when check=False
    return p.returncode, p.stdout if p.stdout is not None else "", p.stderr if p.stderr is not None else ""

def extract_json_objects(s: str) -> list[dict]:
    """Extract JSON objects from arbitrary text by brace scanning."""
    objs, depth, start = [], 0, None
    for i, ch in enumerate(s):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    candidate = s[start:i+1]
                    try:
                        obj = json.loads(candidate)
                        objs.append(obj)
                    except Exception:
                        pass
                    start = None
    return objs

def pass1_probe(src: str, target: float, tp: float, lra: float) -> dict:
    # Keep stderr minimal but loudnorm still prints filter output.
    cmd = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-v", "warning",
        "-i", src,
        "-af", f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json",
        "-f", "null", "-"
    ]
    code, out, err = run(cmd)
    # Find ALL JSON blocks and pick the one that has the 'input_i' key
    for obj in extract_json_objects(err):
        if "input_i" in obj and "input_tp" in obj:
            return obj
    # If not found, print stderr for debugging and fail
    raise RuntimeError("Could not parse loudnorm JSON from pass-1 stderr.\n--- STDERR ---\n" + err)

def pass2_apply(src: str, dst: str, target: float, tp: float, lra: float, meas: dict) -> None:
    mI  = meas.get("input_i")
    mTP = meas.get("input_tp")
    mLR = meas.get("input_lra")
    mTh = meas.get("input_thresh")
    off = meas.get("target_offset")
    if None in (mI, mTP, mLR, mTh, off):
        raise RuntimeError(f"Missing measured parameters from pass-1: {meas}")

    # Light pre-comp helps avoid filter reverting to 'dynamic' unexpectedly
    af = (
        f"acompressor=threshold=-16dB:ratio=3:attack=5:release=80:makeup=4,"
        f"loudnorm=I={target}:TP={tp}:LRA={lra}"
        f":measured_I={mI}:measured_TP={mTP}:measured_LRA={mLR}:measured_thresh={mTh}:offset={off}"
        f":linear=false:print_format=summary"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-v", "warning",
        "-i", src,
        "-af", af,
        "-c:a", "pcm_f32le",
        dst
    ]
    code, out, err = run(cmd)
    if code != 0:
        raise RuntimeError(f"ffmpeg pass-2 failed:\n{err}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--target", type=float, default=-10.0)
    ap.add_argument("--tp", type=float, default=-1.0)
    ap.add_argument("--lra", type=float, default=11.0)
    args = ap.parse_args()

    src = Path(args.src); dst = Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    meas = pass1_probe(str(src), args.target, args.tp, args.lra)
    pass2_apply(str(src), str(dst), args.target, args.tp, args.lra, meas)
    print(json.dumps({"ok": True, "out": str(dst)}, indent=2))

if __name__ == "__main__":
    main()
