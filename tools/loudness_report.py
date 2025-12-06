#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
from datetime import datetime

from security import subprocess as sec_subprocess
from security.config import CONFIG as SEC_CONFIG

FFMPEG = "ffmpeg"  # must be on PATH

def measure_loudness(path: Path) -> dict:
    # Use loudnorm print-only mode to get BS.1770 integrated loudness and TP.
    cmd = [
        FFMPEG, "-hide_banner", "-nostats", "-y",
        "-i", str(path),
        "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
        "-f", "null", "-"
    ]
    proc = sec_subprocess.run_safe(cmd, allow_roots=SEC_CONFIG.allowed_binary_roots, check=True, timeout=SEC_CONFIG.subprocess_timeout)
    out = proc.stdout if proc.stdout is not None else ""
    # loudnorm JSON is printed near the end; find the last JSON block
    start = out.rfind("{")
    end = out.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise RuntimeError(f"Could not parse loudnorm output for {path}")
    meta = json.loads(out[start:end+1])
    return {
        "file": str(path),
        "measured_I_LUFS": _safe_float(meta.get("input_i")),
        "measured_TP_dBTP": _safe_float(meta.get("input_tp")),
        "measured_LRA": _safe_float(meta.get("input_lra")),
        "measured_thresh": _safe_float(meta.get("input_thresh")),
        "analyzed_at": datetime.utcnow().isoformat() + "Z"
    }

def _safe_float(v):
    try:
        return None if v in (None, "nan", "") else float(v)
    except Exception:
        return None

def walk_audio(root: Path):
    exts = {".wav", ".wave", ".aiff", ".aif", ".flac", ".mp3", ".m4a"}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in exts:
            yield p

def main():
    ap = argparse.ArgumentParser(description="Report LUFS/TP for audio files (no modification).")
    ap.add_argument("--root", required=True, help="Folder to scan (e.g., calibration/audio)")
    ap.add_argument("--out-json", default="loudness_report.json")
    ap.add_argument("--out-csv", default="loudness_report.csv")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    rows = []
    for p in walk_audio(root):
        try:
            rows.append(measure_loudness(p))
            print(f"[ok] {p}")
        except Exception as e:
            print(f"[warn] {p}: {e}", file=sys.stderr)

    # Write JSON
    Path(args.out_json).write_text(json.dumps(rows, indent=2))
    # Write CSV
    import csv
    with open(args.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file","measured_I_LUFS","measured_TP_dBTP","measured_LRA","measured_thresh","analyzed_at"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {args.out_json} and {args.out_csv}")

if __name__ == "__main__":
    main()
