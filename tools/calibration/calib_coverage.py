#!/usr/bin/env python3
import argparse, json, os, glob, math
from collections import Counter, defaultdict

TEMPO_BANDS = [
    (70,79),(80,89),(90,99),(100,109),(110,119),(120,129),(130,139),(140,149)
]
def tempo_band(bpm):
    if bpm is None: return "unknown"
    for lo,hi in TEMPO_BANDS:
        if lo <= bpm <= hi:
            return f"{lo}–{hi}"
    return f"{int(bpm//10)*10}–{int(bpm//10)*10+9}"

def runtime_bucket(sec):
    if sec is None: return "unknown"
    if sec < 150: return "<150"
    if sec <= 210: return "150–210"
    return ">210"

def load_float(d,*keys):
    for k in keys:
        if d.get(k) is not None:
            try: return float(d[k])
            except: pass
    return None

def norm_key(name):
    if not name: return "unknown"
    x = name.strip().replace("♯","#").replace("♭","b")
    # enharmonic fold D#->Eb, G#->Ab, A#->Bb, C#->Db, F#->Gb
    enh = {"D#":"Eb","G#":"Ab","A#":"Bb","C#":"Db","F#":"Gb"}
    return enh.get(x, x)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="features_output")
    ap.add_argument("--region", default="US")
    ap.add_argument("--profile", default="Pop")
    args = ap.parse_args()

    packs = glob.glob(os.path.join(args.root,"**","*.pack.json"), recursive=True)
    if not packs:
        print("[coverage] no packs found under", args.root); return 1

    cells = Counter()
    key_hist = Counter()
    mode_hist = Counter()
    total = 0

    for p in packs:
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if d.get("region") != args.region or d.get("profile") != args.profile:
            continue
        f = d.get("features_full") or {}
        bpm = load_float(f, "bpm")
        mode = (f.get("mode") or "").lower() or "unknown"
        dur  = load_float(f, "duration_sec")
        tb   = tempo_band(bpm)
        rb   = runtime_bucket(dur)
        cells[(tb, mode, rb)] += 1
        k = norm_key(f.get("key"))
        key_hist[k] += 1
        mode_hist[mode] += 1
        total += 1

    print(f"[coverage] counted {total} packs for {args.region}/{args.profile}")
    # Print pivot
    print("\nTempoBand × Mode × Runtime bucket:")
    by_tb = defaultdict(Counter)
    for (tb,mode,rb),cnt in sorted(cells.items()):
        by_tb[(tb,mode)][rb] += cnt
    for (tb,mode), row in sorted(by_tb.items()):
        print(f"  {tb:>7} | {mode:<6} | " + " ".join(f"{k}:{row[k]}" for k in ["<150","150–210",">210","unknown"] if row[k]))

    # Gaps
    print("\nGaps (empty cells you might want to fill):")
    for lo,hi in TEMPO_BANDS:
        tb = f"{lo}–{hi}"
        for mode in ["major","minor"]:
            for rb in ["<150","150–210",">210"]:
                if cells[(tb,mode,rb)] == 0:
                    print(f"  - {tb} / {mode} / {rb}")

    # Keys & modes
    print("\nKey histogram (top 8):")
    for k,c in key_hist.most_common(8):
        print(f"  {k}: {c}")
    print("\nMode ratio:")
    total_modes = sum(v for m,v in mode_hist.items() if m!="unknown")
    if total_modes:
        maj = mode_hist.get("major",0)/total_modes
        minr = mode_hist.get("minor",0)/total_modes
        print(f"  major={maj:.2f} minor={minr:.2f}")
    else:
        print("  (no major/minor info)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())