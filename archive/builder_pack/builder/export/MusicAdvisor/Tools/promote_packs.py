#!/usr/bin/env python3
"""
promote_packs.py

Promote candidate JSON files (e.g., MusicAdvisor/Examples/*.json) into
datahub/packs/ as DATA_PACKs:
- Validates minimal shape
- Nests MVP if legacy flat fields were used
- Normalizes tempo en/em dashes → hyphen
- Ensures region/generated_at/MARKET_NORMS.profile present
- Inserts pinned Baseline (reproducibility)
- Builds descriptive filenames: pack_<band>_<rtclass>_<hint>.json
- Deduplicates by (tempo_band, runtime_sec rounded) unless --allow-dupes

Usage:
  python tools/promote_packs.py \
      --src MusicAdvisor/Examples \
      --dst datahub/packs \
      --region US \
      --profile Pop \
      [--hint-from filename|none] \
      [--allow-dupes] \
      [--dry-run] \
      [--verbose]

Examples:
  # Fast path: promote the earlier example_datapack_*.json files
  python tools/promote_packs.py --src MusicAdvisor/Examples --dst datahub/packs --region US --profile Pop --hint-from filename

  # Dry-run to see what would be created
  python tools/promote_packs.py --src MusicAdvisor/Examples --dst datahub/packs --region US --profile Pop --dry-run --verbose
"""
import os, json, re, glob, argparse, time
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

def now_utc():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def normalize_band(band):
    """Accepts '120–129' or '120—129' or '120-129' or numeric; returns 'NN-NN' string or None."""
    if isinstance(band, str):
        s = band.replace("–", "-").replace("—", "-").strip()
        m = re.match(r"^(\d{2,3})-(\d{2,3})$", s)
        if m: return f"{int(m.group(1))}-{int(m.group(2))}"
    elif isinstance(band, (int, float)):
        n = int(round(float(band)))
        if 40 <= n <= 220: return f"{n}-{n}"
    return None

def runtime_class(rt: Optional[float]) -> str:
    if rt is None: return "unk"
    try:
        r = float(rt)
    except Exception:
        return "unk"
    if 160 <= r <= 170: return "short"
    if 171 <= r <= 190: return "mid"
    if 191 <= r <= 210: return "long"
    return "other"

def guess_hint(path: str, mode: str) -> str:
    if mode != "filename": return "fill"
    base = os.path.basename(path).lower()
    # crude but useful tags
    if "guitar" in base: return "guitar"
    if "synth" in base: return "synth"
    if "radio" in base: return "radio"
    if "ballad" in base: return "ballad"
    if "groove" in base: return "groove"
    if "indie" in base: return "indie"
    if "vocal" in base or "vox" in base or "stack" in base: return "vocal"
    if "pad" in base or "retro" in base: return "pad"
    if "sync" in base: return "sync"
    return "fill"

def ensure_datapack(doc: Dict[str, Any], region: str, profile: str, ts: str) -> Tuple[Dict[str, Any], str, float]:
    """
    Returns (patched_doc, tempo_band_str, runtime_float).
    Applies:
      - region / generated_at / MARKET_NORMS.profile defaults
      - nest MVP and ensure keys
      - normalize tempo band hyphen
      - pin Baseline
      - Known_Gaps array
    """
    out = json.loads(json.dumps(doc))  # deep copy

    # Core presence
    out["region"] = out.get("region") or region
    out["generated_at"] = out.get("generated_at") or ts
    mn = out.get("MARKET_NORMS") or {}
    if not isinstance(mn, dict):
        mn = {}
    mn["profile"] = mn.get("profile") or profile
    out["MARKET_NORMS"] = mn

    # MVP nesting + defaults
    mvp = out.get("MVP")
    if not isinstance(mvp, dict):
        mvp = {}
        # migrate legacy
        for k in ("tempo_band_bpm", "runtime_sec", "ttc_sec", "exposures"):
            if k in out: mvp[k] = out[k]
    # defaults
    mvp.setdefault("tempo_band_bpm", "120-129")
    mvp.setdefault("runtime_sec", 176.07)
    mvp.setdefault("ttc_sec", None)
    mvp.setdefault("exposures", None)
    # normalize band
    norm = normalize_band(mvp.get("tempo_band_bpm"))
    if not norm:
        # if invalid, normalize to default and mark gap
        norm = "120-129"
        out.setdefault("Known_Gaps", []).append("tempo_band_bpm invalid → defaulted 120-129")
    mvp["tempo_band_bpm"] = norm
    out["MVP"] = mvp

    # clean legacy top-level MVP keys (avoid ambiguity)
    for k in ("tempo_band_bpm", "runtime_sec", "ttc_sec", "exposures"):
        if k in out: del out[k]

    # Baseline pinned (reproducibility)
    base = out.get("Baseline")
    if not isinstance(base, dict):
        base = {}
    base.setdefault("active_profile", mn["profile"])
    base.setdefault("effective_utc", ts)
    base["pinned"] = True
    base.setdefault("previous_profile", None)
    base.setdefault("note", "Promoted & pinned for reproducibility")
    out["Baseline"] = base

    # Known_Gaps array present
    out.setdefault("Known_Gaps", [])

    # Extract normalized values
    band_str = out["MVP"]["tempo_band_bpm"]
    try:
        runtime = float(out["MVP"]["runtime_sec"])
    except Exception:
        runtime = 176.07  # safe default
        out["MVP"]["runtime_sec"] = runtime
        if "MVP.runtime_sec invalid → defaulted 176.07" not in out["Known_Gaps"]:
            out["Known_Gaps"].append("MVP.runtime_sec invalid → defaulted 176.07")

    return out, band_str, runtime

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Source folder with candidate JSONs (e.g., MusicAdvisor/Examples)")
    ap.add_argument("--dst", required=True, help="Destination folder (e.g., datahub/packs)")
    ap.add_argument("--region", default="US")
    ap.add_argument("--profile", default="Pop")
    ap.add_argument("--hint-from", choices=["filename", "none"], default="filename")
    ap.add_argument("--allow-dupes", action="store_true", help="Allow duplicates with same (band, runtime_rounded)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    src = args.src
    dst = args.dst
    ts = now_utc()

    if not os.path.isdir(src):
        print(f"[ERR] Source folder not found: {src}")
        raise SystemExit(1)
    if not os.path.isdir(dst):
        os.makedirs(dst, exist_ok=True)

    # Gather source files
    files = sorted(glob.glob(os.path.join(src, "*.json")))
    if not files:
        print(f"[WARN] No JSON files in {src}")
        raise SystemExit(1)

    seen_keys = set()
    promoted = []

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            print(f"[SKIP] {fp} (parse error: {e})")
            continue

        patched, band, rt = ensure_datapack(doc, args.region, args.profile, ts)
        rt_class = runtime_class(rt)
        rt_key = int(round(rt))
        dup_key = (band, rt_key)

        if not args.allow_dupes and dup_key in seen_keys:
            if args.verbose:
                print(f"[DUPE] Skip {fp} -> (band={band}, rt≈{rt_key}) already promoted")
            continue

        seen_keys.add(dup_key)
        hint = guess_hint(fp, args.hint_from)
        out_name = f"pack_{band}_{rt_class}_{hint}.json"
        # Ensure uniqueness of filename
        out_path = os.path.join(dst, out_name)
        i = 2
        while os.path.exists(out_path):
            out_path = os.path.join(dst, f"pack_{band}_{rt_class}_{hint}_{i}.json")
            i += 1

        if args.verbose or args.dry_run:
            rel = os.path.relpath(out_path)
            print(f"[READY] {fp} -> {rel} (band={band}, runtime={rt:.2f}s, class={rt_class})")

        if not args.dry_run:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(patched, f, indent=2, ensure_ascii=False)
            promoted.append(out_path)

    print(f"[DONE] Promoted {len(promoted)} file(s) to {dst}")
    if promoted and args.verbose:
        for p in promoted:
            print(" -", os.path.relpath(p))

if __name__ == "__main__":
    main()
