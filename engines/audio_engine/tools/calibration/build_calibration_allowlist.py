#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from statistics import mean

from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from hci_calibrator import fit_affine_for_anchor

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs-root", required=True)
    ap.add_argument("--allowlist-anchors", required=True, help="comma-separated")
    ap.add_argument("--outfile", required=True)
    ap.add_argument("--cap-min", type=float, default=0.05)
    ap.add_argument("--cap-max", type=float, default=0.98)
    ap.add_argument("--target-means", default="", help="a=b,c=d overrides")
    args = ap.parse_args()

    allow = [a.strip() for a in args.allowlist_anchors.split(",") if a.strip()]

    # Defaults that worked for you earlier
    default_targets = {
        "00_core_modern": 0.697,
        "01_echo_1985_89": 0.671,
        "02_echo_1990_94": 0.668,
        "03_echo_1995_99": 0.664,
        "04_echo_2000_04": 0.660,
        "05_echo_2005_09": 0.668,
        "06_echo_2010_14": 0.665,
        "07_echo_2015_19": 0.688,
        "08_echo_2020_24": 0.721,
        "99_legacy_pop_eval": 0.677
    }

    # Parse overrides, if any
    if args.target_means:
        for token in args.target_means.split(","):
            k, v = token.split("=")
            default_targets[k.strip()] = float(v)

    buckets = {a: [] for a in allow}
    packs = list(Path(args.packs_root).rglob("**/_packs/**/*.pack.json"))
    for p in packs:
        try:
            d = json.loads(p.read_text())
            a = d.get("anchor")
            if a not in allow:
                continue
            h = d.get("HCI_v1") or {}
            raw = h.get("HCI_v1_raw")
            if raw is None:
                raw = h.get("HCI_v1_score") or d.get("HCI_v1_score")
            if raw is not None:
                buckets[a].append(float(raw))
        except Exception:
            pass

    anchors_out = {}
    for a in allow:
        vals = buckets.get(a, [])
        if not vals:
            anchors_out[a] = {"target_mean": default_targets.get(a), "scale": 1.0, "offset": 0.0, "raw_mean": None}
        else:
            tgt = default_targets.get(a, min(0.9, max(0.6, mean(vals)+0.20)))
            scale, offset = fit_affine_for_anchor(vals, tgt)
            anchors_out[a] = {"target_mean": tgt, "scale": scale, "offset": offset, "raw_mean": mean(vals)}

    out = {
        "cap_min": args.cap_min,
        "cap_max": args.cap_max,
        "anchors": anchors_out,
        "notes": "Built from allowlist with explicit targets."
    }
    Path(args.outfile).parent.mkdir(parents=True, exist_ok=True)
    Path(args.outfile).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[calibration] wrote {args.outfile}")

if __name__ == "__main__":
    main()
