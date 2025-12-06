#!/usr/bin/env python3
"""
Per-song "before → after" peek. Given a pack.json and a calibration config,
prints a mini meter and the delta.

Usage:
  python calibration_peek.py \
    --pack "/path/to/_packs/...pack.json" \
    --calib /path/to/hci_calibration.json
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def load_mapping(calib_path: Path):
    d = json.loads(calib_path.read_text())
    nodes = [(float(n["x"]), float(n["y"])) for n in d["mapping"]["nodes"]]
    nodes.sort()
    def f(x: float) -> float:
        x = max(0.0, min(1.0, float(x)))
        for i in range(len(nodes)-1):
            x0,y0 = nodes[i]; x1,y1 = nodes[i+1]
            if x <= x1:
                if x1 == x0: return y1
                t = (x-x0)/(x1-x0)
                return y0 + t*(y1-y0)
        return nodes[-1][1]
    return f

def bar(x, w=30, fill="█"):
    k = max(0,min(w,int(round(x*w))))
    return fill*k + " "*(w-k)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True)
    ap.add_argument("--calib", required=True)
    args = ap.parse_args()

    d = json.loads(Path(args.pack).read_text())
    raw = float(d.get("HCI_v1",{}).get("HCI_v1_score"))
    calibrate = load_mapping(Path(args.calib))
    cal = calibrate(raw)
    delta = cal - raw

    name = d.get("audio_name") or d.get("source_audio") or Path(args.pack).name
    print(f"=== HCI Peek — {name} ===")
    print(f"RAW        : {raw:0.3f} |{bar(raw)}|")
    print(f"CALIBRATED : {cal:0.3f} |{bar(cal)}|   (Δ={delta:+.3f})")
    src = d.get("Calibration",{}).get("source") or "pack/local"
    print(f"calib source: {src}")

if __name__ == "__main__":
    main()
