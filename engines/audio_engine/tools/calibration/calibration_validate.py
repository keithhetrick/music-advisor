#!/usr/bin/env python3
import argparse, json, math
from pathlib import Path
from statistics import mean
from glob import glob
from scipy.stats import spearmanr  # if needed: pip install scipy

def load_calibration(calib_path):
    d = json.loads(Path(calib_path).read_text())
    # New anchors schema
    if "anchors" in d:
        return {
            "mode": "anchors",
            "cap_min": float(d.get("cap_min", 0.0)),
            "cap_max": float(d.get("cap_max", 1.0)),
            "anchors": d["anchors"],  # {anchor: {target_mean, scale, offset, raw_mean}}
        }
    # Legacy schema (not used here)
    if "nodes" in d or "knots" in d:
        return {"mode": "spline", "raw": d}
    raise KeyError("Calibration JSON missing anchors or nodes/knots.")

def list_packs(packs_root):
    return glob(str(Path(packs_root).joinpath("**/_packs/**/*.pack.json")), recursive=True)

def get_anchor(pack_dict):
    return pack_dict.get("anchor") or "UNKNOWN"

def get_raw(pack_dict):
    h = pack_dict.get("HCI_v1") or {}
    v = h.get("HCI_v1_raw")
    if v is None:
        v = h.get("HCI_v1_score") or pack_dict.get("HCI_v1_score")
    return None if v is None else float(v)

def cap(x, lo, hi):
    return max(lo, min(hi, x))

def ascii_bar(x, length=20, fill="█"):
    """Render a simple bar for x in [0,1]."""
    try:
        x = float(x)
        length = int(length)  # defensive
        n = max(0, min(length, int(round(x * length))))
    except Exception:
        n = 0
        length = 20
    return fill * n + " " * (length - n)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs-root", required=True)
    ap.add_argument("--calib", required=True)
    ap.add_argument("--out-txt", default=None)
    ap.add_argument("--out-png", default=None)  # kept for CLI compatibility; not used here
    args = ap.parse_args()

    calib = load_calibration(args.calib)
    packs = list_packs(args.packs_root)

    rows = []       # per-song tuples: (anchor, raw, cal, target_mean)
    buckets = {}    # anchor -> list[(raw, cal)]
    targets = {}    # anchor -> target_mean

    if calib["mode"] == "anchors":
        cap_min = calib["cap_min"]; cap_max = calib["cap_max"]
        anchors_cfg = calib["anchors"]

        for p in packs:
            try:
                d = json.loads(Path(p).read_text())
                a = get_anchor(d)
                raw = get_raw(d)
                if raw is None or a not in anchors_cfg:
                    continue
                sc = float(anchors_cfg[a].get("scale", 1.0))
                off = float(anchors_cfg[a].get("offset", 0.0))
                cal = cap(sc * raw + off, cap_min, cap_max)
                tgt = anchors_cfg[a].get("target_mean")
                rows.append((a, raw, cal, tgt))
                buckets.setdefault(a, []).append((raw, cal))
                if tgt is not None:
                    targets[a] = float(tgt)
            except Exception:
                pass
    else:
        raise NotImplementedError("This validator currently focuses on anchors schema.")

    # song-level errors vs per-anchor target means
    raw_err, cal_err, raw_vals, cal_vals, tgt_vals = [], [], [], [], []
    for a, raw, cal, tgt in rows:
        if tgt is None:
            continue
        tgt = float(tgt)
        raw_err.append(abs(raw - tgt))
        cal_err.append(abs(cal - tgt))
        raw_vals.append(raw); cal_vals.append(cal); tgt_vals.append(tgt)

    mae_raw = mean(raw_err) if raw_err else float("nan")
    mae_cal = mean(cal_err) if cal_err else float("nan")
    s_raw = spearmanr(raw_vals, tgt_vals).correlation if len(raw_vals) > 1 else float("nan")
    s_cal = spearmanr(cal_vals, tgt_vals).correlation if len(cal_vals) > 1 else float("nan")

    # anchor-level means vs targets
    anchor_lines = []
    s_anchor_raw = float("nan"); s_anchor_cal = float("nan")
    if buckets and targets:
        anchors_all = sorted(set(buckets.keys()) & set(targets.keys()))
        means_raw, means_cal, means_tgt = [], [], []
        for a in anchors_all:
            vals = buckets[a]
            if not vals:
                continue
            mr = mean([r for (r, _c) in vals])
            mc = mean([c for (_r, c) in vals])
            mt = float(targets[a])
            means_raw.append(mr); means_cal.append(mc); means_tgt.append(mt)
            anchor_lines.append(
                f"{a:27s} [{ascii_bar(mr)}] [{ascii_bar(mc)}] [{ascii_bar(mt, fill='░')}]     {abs(mr-mt):7.3f}  {abs(mc-mt):7.3f}"
            )
        if len(means_raw) > 1:
            s_anchor_raw = spearmanr(means_raw, means_tgt).correlation
            s_anchor_cal = spearmanr(means_cal, means_tgt).correlation

    # report
    print("=== CALIBRATION VALIDATION (anchors) ===")
    print(f"packs_root: {args.packs_root}")
    print(f"calib_map : {args.calib}\n")
    print("Global metrics:")
    print(f"  MAE raw → target        : {mae_raw:.3f}")
    print(f"  MAE calibrated → target : {mae_cal:.3f}   (Δ={mae_raw - mae_cal:+.3f})")
    print(f"  Spearman (song-level)   : raw={s_raw if not math.isnan(s_raw) else 'nan'}  cal={s_cal if not math.isnan(s_cal) else 'nan'}")
    print(f"  Spearman (anchor means) : raw={s_anchor_raw if not math.isnan(s_anchor_raw) else 'nan'}  cal={s_anchor_cal if not math.isnan(s_anchor_cal) else 'nan'}\n")
    print("Anchor means (bars are 0..1):")
    print("ANCHOR                         RAW                CAL                TARGET    |err_raw  err_cal|")
    for line in anchor_lines:
        print(line)

    if args.out_txt:
        Path(args.out_txt).write_text("\n".join([
            "MAE_raw="+str(mae_raw),
            "MAE_cal="+str(mae_cal),
            "Spearman_song_raw="+str(s_raw),
            "Spearman_song_cal="+str(s_cal),
            "Spearman_anchor_raw="+str(s_anchor_raw),
            "Spearman_anchor_cal="+str(s_anchor_cal),
        ]))
        print(f"\n[wrote] {args.out_txt}")

if __name__ == "__main__":
    main()
