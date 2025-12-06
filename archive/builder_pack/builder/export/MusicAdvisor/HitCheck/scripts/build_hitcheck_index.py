import argparse, os, sys, yaml
from ..hitcheck.index_builder import build_index

def err(msg):
    print(f"[HitCheck] {msg}", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(description="Build HitCheck index")
    ap.add_argument("--cfg", required=True, help="Path to config.yaml")
    ap.add_argument("--features", help="Override features.csv")
    ap.add_argument("--meta", help="Override meta.json")
    ap.add_argument("--out", help="Override output index npz path")
    args = ap.parse_args()

    with open(args.cfg, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    paths = cfg.get("paths", {})

    features = args.features or paths.get("reference_features")
    meta     = args.meta or paths.get("reference_meta")
    out_npz  = args.out or paths.get("index_npz")

    if not features or not os.path.exists(features):
        err(f"Missing features.csv: {features}")
        sys.exit(2)
    if not meta or not os.path.exists(meta):
        err(f"Missing meta.json: {meta}")
        sys.exit(2)
    if not out_npz:
        err("Missing output index_npz path")
        sys.exit(2)

    os.makedirs(os.path.dirname(out_npz), exist_ok=True)

    print("[HitCheck] Building index…")
    build_index(features, meta, out_npz)
    print(f"[HitCheck] ✅ Saved index → {out_npz}")

if __name__ == "__main__":
    main()
