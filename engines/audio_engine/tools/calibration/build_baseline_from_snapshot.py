#!/usr/bin/env python3
import argparse, json, os, math, datetime
from collections import Counter
from adapters.bootstrap import ensure_repo_root
ensure_repo_root()

from adapters import add_log_sandbox_arg, apply_log_sandbox_env
from adapters import make_logger
from adapters import utc_now_iso

LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]

def quarter_of(dt):
    return (dt.month-1)//3 + 1

def norm_key(name):
    if not name: return None
    x = name.strip().replace("♯","#").replace("♭","b")
    enh = {"D#":"Eb","G#":"Ab","A#":"Bb","C#":"Db","F#":"Gb"}
    return enh.get(x, x)

def safe_mean(xs):
    xs = [x for x in xs if x is not None]
    if not xs: return None
    return sum(xs)/len(xs)

def safe_std(xs, mean=None):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2: return None
    m = mean if mean is not None else sum(xs)/len(xs)
    var = sum((x-m)**2 for x in xs)/(len(xs)-1)
    return var**0.5

def build_tempo_bands(bpm_list):
    # 10-bpm bands (98–126 preference will emerge naturally)
    hist = Counter()
    for b in bpm_list:
        if b is None: continue
        lo = int(b//10)*10; hi = lo+9
        label = f"{lo}–{hi}"
        hist[label]+=1
    top = [k for k,_ in hist.most_common(3)]
    return top, hist

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--region", default="US")
    ap.add_argument("--profile", default="Pop")
    ap.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    ap.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    redact_flag = args.log_redact or LOG_REDACT
    redact_values = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or LOG_REDACT_VALUES
    )
    log = make_logger("build_baseline_from_snapshot", redact=redact_flag, secrets=redact_values)

    snap = json.load(open(args.snapshot))
    packs = [p for p in snap.get("packs",[]) if p.get("region")==args.region and p.get("profile")==args.profile]
    if not packs:
        log("[baseline] no packs in snapshot for region/profile"); return 1

    bpms, durs, keys, modes = [], [], [], []
    for p in packs:
        f = p.get("features_full") or {}
        b = f.get("bpm")
        d = f.get("duration_sec") or p.get("features",{}).get("runtime_sec")
        try: b = float(b) if b is not None else None
        except: b = None
        try: d = float(d) if d is not None else None
        except: d = None
        bpms.append(b)
        durs.append(d)
        keys.append(norm_key(f.get("key")))
        m = (f.get("mode") or "").lower() if f.get("mode") else None
        modes.append(m)

    tempo_mean = safe_mean(bpms); tempo_std = safe_std(bpms, tempo_mean)
    run_mean   = safe_mean(durs); run_std   = safe_std(durs, run_mean)

    key_hist = Counter(k for k in keys if k)
    total_modes = sum(1 for m in modes if m in ("major","minor"))
    maj = sum(1 for m in modes if m=="major")
    minr= sum(1 for m in modes if m=="minor")
    mode_ratio = {"major": round(maj/total_modes,2) if total_modes else None,
                  "minor": round(minr/total_modes,2) if total_modes else None}

    top_bands, band_hist = build_tempo_bands(bpms)

    # Build object
    out = {
        "id": None,  # filled below
        "MARKET_NORMS": {
            "tempo_bpm_mean": round(tempo_mean,2) if tempo_mean is not None else None,
            "tempo_bpm_std": round(tempo_std,2) if tempo_std is not None else None,
            "tempo_band_pref": top_bands,
            "key_distribution": {k: round(v/sum(key_hist.values()),2) for k,v in key_hist.items()} if key_hist else {},
            "mode_ratio": mode_ratio,
            "runtime_sec_mean": round(run_mean,2) if run_mean is not None else None,
            "runtime_sec_std": round(run_std,2) if run_std is not None else None
        },
        "META": {
            "source_snapshot": os.path.basename(args.snapshot),
            "region": args.region,
            "profile": args.profile,
            "generated_at": datetime.datetime.utcnow().isoformat()+"Z",
            "tempo_band_hist": dict(band_hist)
        }
    }

    now = datetime.datetime.utcnow()
    q = quarter_of(now)
    out_id = f"{args.region}_{args.profile}_Cal_Baseline_{now.year}Q{q}.json"
    out["id"] = out_id

    out_dir = os.path.join("datahub","cohorts")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, out_id)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    log(f"[baseline] wrote {out_path} @ {utc_now_iso()}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
