#!/usr/bin/env python3
import argparse, json, csv
from pathlib import Path
from glob import glob
from ma_config.paths import get_calibration_root

def list_packs(root):
    return glob(str(Path(root).joinpath("**/_packs/**/*.pack.json")), recursive=True)

def get_anchor(d): return d.get("anchor") or "UNKNOWN"
def get_title(d):  return d.get("title") or d.get("song") or Path(d.get("_path","?")).stem

def get_raw(d):
    h = d.get("HCI_v1") or {}
    v = h.get("HCI_v1_raw")
    if v is None: v = h.get("HCI_v1_score") or d.get("HCI_v1_score")
    return None if v is None else float(v)

def get_calibrated(d):
    h = d.get("HCI_v1") or {}
    v = h.get("HCI_v1_calibrated")
    return None if v is None else float(v)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs-root", required=True)
    default_out = get_calibration_root() / "hci_before_after.csv"
    ap.add_argument("--out-csv", default=str(default_out))
    args = ap.parse_args()

    rows=[]
    for p in list_packs(args.packs_root):
        try:
            d = json.loads(Path(p).read_text())
        except Exception:
            continue
        anchor = get_anchor(d)
        title  = get_title(d)
        raw = get_raw(d)
        cal = get_calibrated(d)
        if raw is None: continue
        rows.append({"anchor":anchor,"title":title,"raw":raw,"calibrated":cal,"pack":p})

    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_csv, "w", newline="") as f:
        w=csv.DictWriter(f, fieldnames=["anchor","title","raw","calibrated","pack"])
        w.writeheader(); w.writerows(rows)
    print(f"[report] wrote {args.out_csv} ({len(rows)} rows)")

if __name__ == "__main__":
    main()
