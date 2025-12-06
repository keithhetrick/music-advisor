#!/usr/bin/env python3
import argparse, json, os, glob, datetime

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="features_output")
    ap.add_argument("--region", default="US")
    ap.add_argument("--profile", default="Pop")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    packs = []
    for p in glob.glob(os.path.join(args.root,"**","*.pack.json"), recursive=True):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if d.get("region")==args.region and d.get("profile")==args.profile:
            packs.append(d)

    snap = {
        "schema":"ma.calibration.v1",
        "region": args.region,
        "profile": args.profile,
        "generated_at": datetime.datetime.utcnow().isoformat()+"Z",
        "count": len(packs),
        "packs": packs
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out,"w") as f:
        json.dump(snap,f,indent=2)
    print(f"[snapshot] wrote {args.out} with {len(packs)} packs.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
