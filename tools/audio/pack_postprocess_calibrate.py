#!/usr/bin/env python3
import argparse, json, sys, glob, os
from pathlib import Path

def load_calib(path):
    with open(path) as f:
        return json.load(f)

def load_pack(p):
    with open(p) as f:
        return json.load(f)

def save_pack(p, d):
    tmp = str(p)+".tmp"
    with open(tmp, "w") as f: json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs-root", required=True)
    ap.add_argument("--calibration", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    calib = load_calib(args.calibration)
    anchors = calib.get("anchors", {})
    cap_min = calib.get("cap_min", 0.0)
    cap_max = calib.get("cap_max", 1.0)

    packs = sorted(Path(args.packs_root).rglob("**/_packs/**/*.pack.json"))
    changed = 0
    for p in packs:
        try:
            d = load_pack(p)
            anchor = d.get("anchor")
            hv1 = d.get("HCI_v1") or {}
            raw = hv1.get("HCI_v1_raw") or hv1.get("HCI_v1_score") or d.get("HCI_v1_score")
            if raw is None:
                continue
            raw = float(raw)
            if anchor in anchors:
                cfg = anchors[anchor]
                scale = float(cfg.get("scale", 1.0))
                offset = float(cfg.get("offset", 0.0))
                cal = max(cap_min, min(cap_max, scale*raw + offset))
                hv1["HCI_v1_raw"] = raw
                hv1["HCI_v1_calibrated"] = cal
                hv1["HCI_v1_source"] = "calibrated"
                d["HCI_v1"] = hv1
                if args.write:
                    save_pack(p, d)
                changed += 1
            else:
                # keep raw; mark source
                hv1["HCI_v1_raw"] = raw
                hv1["HCI_v1_source"] = hv1.get("HCI_v1_source","raw")
                d["HCI_v1"] = hv1
                if args.write:
                    save_pack(p, d)
        except Exception as e:
            print(f"[calibrate] skip {p}: {e}", file=sys.stderr)

    print(f"[calibrate] processed {changed} packs. ({'written' if args.write else 'dry-run'})")

if __name__ == "__main__":
    main()
