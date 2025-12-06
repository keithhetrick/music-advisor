#!/usr/bin/env python3
"""
Summarize raw and (optional) calibrated HCI across the calibration packs.
- Reads *.pack.json under **_packs** rooted at --packs-root
- If --calib is provided, applies the piecewise-linear mapping and reports both.

Usage:
  python calibration_report.py \
    --packs-root "/.../audio_norm" \
    [--calib /path/to/hci_calibration.json]
"""
from __future__ import annotations
import argparse, json, statistics, sys
from pathlib import Path
from collections import defaultdict

def load_mapping(calib_path: Path):
    d = json.loads(calib_path.read_text())
    nodes = [(float(n["x"]), float(n["y"])) for n in d["mapping"]["nodes"]]
    nodes.sort()
    def f(x: float) -> float:
        x = max(0.0, min(1.0, x))
        # linear interp between nodes
        for i in range(len(nodes) - 1):
            x0, y0 = nodes[i]
            x1, y1 = nodes[i+1]
            if x <= x1:
                if x1 == x0:
                    return y1
                t = (x - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return nodes[-1][1]
    return f

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs-root", required=True)
    ap.add_argument("--calib", default=None)
    args = ap.parse_args()

    packs_root = Path(args.packs_root).expanduser().resolve()
    if not packs_root.is_dir():
        print(f"[report] not a dir: {packs_root}", file=sys.stderr); sys.exit(2)

    calibrate = None
    if args.calib:
        calibrate = load_mapping(Path(args.calib))

    bucket = defaultdict(list)
    for pack in packs_root.rglob("**/_packs/**/*.pack.json"):
        parts = list(pack.parts)
        if "_packs" not in parts:
            continue
        idx = parts.index("_packs")
        if idx == 0: 
            continue
        anchor = parts[idx-1]
        try:
            d = json.loads(pack.read_text())
            raw = float(d.get("HCI_v1",{}).get("HCI_v1_score"))
        except Exception:
            continue
        bucket[anchor].append(raw)

    anchors = sorted(bucket.keys())
    print("ANCHOR                          N    RAW_MEAN  RAW_MED  RAW_STD   CAL_MEAN  CAL_MED  CAL_STD")
    for a in anchors:
        vals = bucket[a]
        n = len(vals)
        mean = statistics.fmean(vals)
        med  = statistics.median(vals)
        std  = statistics.pstdev(vals) if n>1 else 0.0
        if calibrate:
            cvals = [calibrate(v) for v in vals]
            cmean = statistics.fmean(cvals)
            cmed  = statistics.median(cvals)
            cstd  = statistics.pstdev(cvals) if n>1 else 0.0
            print(f"{a:30s} {n:4d}   {mean:7.3f}  {med:7.3f}  {std:7.3f}   {cmean:7.3f}  {cmed:7.3f}  {cstd:7.3f}")
        else:
            print(f"{a:30s} {n:4d}   {mean:7.3f}  {med:7.3f}  {std:7.3f}")

if __name__ == "__main__":
    main()
