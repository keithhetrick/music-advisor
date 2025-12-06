#!/usr/bin/env python3
"""
Auto-Cohort Composer
- Scans /datahub/packs/*.json
- Validates minimal DATA_PACK shape (region, generated_at, MARKET_NORMS.profile, MVP.{tempo_band_bpm,runtime_sec})
- Picks a balanced 10-pack cohort across tempo/runtime bands
- Writes /datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json
"""
import json, os, re, glob, sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACKS_DIR = os.path.join(ROOT, "datahub", "packs")
COHORTS_DIR = os.path.join(ROOT, "datahub", "cohorts")
BASELINE_ID = "US_Pop_Baseline_2025"
COHORT_ID = "US_Pop_Cal_Baseline_2025Q4"

TEMPO_BUCKETS = [
    (100,110), (112,118), (118,122), (122,126), (126,129), ("wild", "wild")
]
RUNTIME_CLASSES = {"short": (160,170), "mid": (171,190), "long": (191,210)}

def parse_band(s):
    if isinstance(s, str):
        s = s.replace("–","-").replace("—","-").strip()
        m = re.match(r"^(\d{2,3})-(\d{2,3})$", s)
        if m: return (int(m.group(1)), int(m.group(2)))
    if isinstance(s, (int, float)):
        return (int(s), int(s))
    return None

def runtime_class(rt):
    if rt is None: return None
    for name,(lo,hi) in RUNTIME_CLASSES.items():
        if lo <= rt <= hi: return name
    return "other"

def validate(dp):
    ok = True
    def miss(x):
        nonlocal ok; ok=False; return False
    if not isinstance(dp, dict): return False
    if not dp.get("region"): miss("region")
    ts = dp.get("generated_at")
    if not isinstance(ts, str) or ("T" not in ts): miss("generated_at")
    mn = dp.get("MARKET_NORMS", {})
    if not isinstance(mn, dict) or not mn.get("profile"): miss("MARKET_NORMS.profile")
    mvp = dp.get("MVP", {})
    if not isinstance(mvp, dict): miss("MVP")
    tb = parse_band(mvp.get("tempo_band_bpm"))
    if not tb: miss("tempo_band_bpm")
    rt = mvp.get("runtime_sec")
    if not isinstance(rt, (int, float)): miss("runtime_sec")
    return ok

def load_packs():
    packs = []
    for path in sorted(glob.glob(os.path.join(PACKS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            try:
                dp = json.load(f)
            except Exception:
                continue
        if not validate(dp): continue
        tb = parse_band(dp["MVP"]["tempo_band_bpm"])
        rt = float(dp["MVP"]["runtime_sec"])
        packs.append({
            "path": os.path.relpath(path, ROOT).replace("\\","/"),
            "tempo_band": tb, "runtime": rt,
            "rt_class": runtime_class(rt)
        })
    return packs

def choose_cohort(packs):
    chosen, used = [], set()

    def pick_bucket(lo,hi, quota, runtime_pref=None):
        nonlocal chosen, used
        cand = []
        for p in packs:
            if p["path"] in used: continue
            lo_p, hi_p = p["tempo_band"]
            hit = (lo=="wild") or (lo <= lo_p and hi_p <= hi)
            if hit: cand.append(p)
        # stable deterministic order: prefer runtime class if provided, then middle-ish runtime
        cand.sort(key=lambda x: (0 if (runtime_pref and x["rt_class"]==runtime_pref) else 1,
                                 abs(x["runtime"]-176.0), x["path"]))
        take = cand[:quota]
        for t in take:
            used.add(t["path"]); chosen.append(t)

    # Coverage plan: 1,1,2,3,2,1 (wild)
    pick_bucket(100,110,1,"long")
    pick_bucket(112,118,1,"mid")
    pick_bucket(118,122,2)
    pick_bucket(122,126,3)
    pick_bucket(126,129,2)
    pick_bucket("wild","wild",1)

    # if less than 10, top up by closeness to 176s irrespective of band
    if len(chosen) < 10:
        remain = [p for p in packs if p["path"] not in used]
        remain.sort(key=lambda x: (abs(x["runtime"]-176.0), x["path"]))
        for p in remain:
            if len(chosen) >= 10: break
            used.add(p["path"]); chosen.append(p)
    return chosen[:10]

def write_cohort(chosen):
    os.makedirs(COHORTS_DIR, exist_ok=True)
    out_path = os.path.join(COHORTS_DIR, f"{COHORT_ID}.json")
    now = datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
    doc = {
        "cohort_id": COHORT_ID,
        "baseline_id": BASELINE_ID,
        "region": "US",
        "profile": "Pop",
        "effective_utc": now,
        "note": "Auto-generated calibration cohort for US Pop",
        "packs": [c["path"] for c in chosen],
        "Baseline": {
            "active_profile": "Pop",
            "effective_utc": now,
            "pinned": True,
            "note": "Pinned reference for reproducibility"
        },
        "Known_Gaps": []
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"Wrote cohort: {out_path}")
    for p in doc["packs"]: print(" -", p)

def main():
    packs = load_packs()
    if not packs:
        print("No valid packs found in /datahub/packs. Add JSONs first."); sys.exit(1)
    chosen = choose_cohort(packs)
    write_cohort(chosen)

if __name__ == "__main__":
    main()
