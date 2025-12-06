# Aggregate packs -> compute MARKET_NORMS and write cohort JSON.
from __future__ import annotations
import json, math, sys
from pathlib import Path
from typing import Dict, Any, List

"""
Aggregate packs -> compute MARKET_NORMS and write datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json

Usage:
  python aggregate_stats.py \
      --packs-root features_output \
      --include "*/00_core_modern/*/*.pack.json" \
      --include "*/20_2015_2019/*/*.pack.json" \
      --include "*/21_2020_2024/*/*.pack.json" \
      --out datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json
"""

def _glob_all(root: Path, patterns: List[str]) -> List[Path]:
    out: List[Path] = []
    for pat in patterns:
        out += list(root.glob(pat))
    return out

def _mean_std(xs: List[float]) -> (float, float):
    if not xs: return (None, None)
    m = sum(xs)/len(xs)
    v = sum((x-m)**2 for x in xs)/max(1,(len(xs)-1))
    return (m, math.sqrt(v))

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs-root", required=True)
    ap.add_argument("--include", action="append", required=True, help="glob relative to packs-root")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.packs_root)
    packs = _glob_all(root, args.include)

    bpms: List[float]=[]
    runs: List[float]=[]
    lufs: List[float]=[]
    modes: Dict[str,int] = {}
    keys: Dict[str,int] = {}
    tempo_bands: Dict[str,int] = {}

    def band_of(bpm: float) -> str:
        if bpm is None: return "unknown"
        # 10-bpm buckets aligned at 100–109 etc.
        lo = (int(bpm)//10)*10
        hi = lo+9
        return f"{lo}–{hi}"

    for p in packs:
        try:
            d = json.loads(p.read_text())
            ff = d.get("features_full",{})
            bpm=ff.get("bpm"); dur=ff.get("duration_sec"); lu=ff.get("loudness_lufs")
            key=ff.get("key"); mode=ff.get("mode")
            if isinstance(bpm,(int,float)): bpms.append(float(bpm))
            if isinstance(dur,(int,float)): runs.append(float(dur))
            if isinstance(lu,(int,float)): lufs.append(float(lu))
            if isinstance(key,str): keys[key]=keys.get(key,0)+1
            if isinstance(mode,str): modes[mode]=modes.get(mode,0)+1
            b = band_of(bpm)
            tempo_bands[b] = tempo_bands.get(b,0)+1
        except Exception:
            pass

    mu_bpm, sd_bpm = _mean_std(bpms)
    mu_run, sd_run = _mean_std(runs)
    mu_lufs, sd_lufs = _mean_std(lufs)
    total_modes = sum(modes.values()) or 1
    mode_ratio = {k: round(v/total_modes,2) for k,v in modes.items()}
    total_keys = sum(keys.values()) or 1
    key_distribution = {k: round(v/total_keys,2) for k,v in keys.items()}

    # Top 3 bands by frequency
    band_sorted = sorted(((k,v) for k,v in tempo_bands.items() if k!="unknown"), key=lambda x: x[1], reverse=True)
    tempo_band_pref = [k for k,_ in band_sorted[:3]]

    out = {
      "id": "US_Pop_Cal_Baseline_2025Q4.json",
      "MARKET_NORMS": {
        "tempo_bpm_mean": round(mu_bpm,2) if mu_bpm is not None else None,
        "tempo_bpm_std": round(sd_bpm,2) if sd_bpm is not None else None,
        "tempo_band_pref": tempo_band_pref,
        "key_distribution": key_distribution,
        "mode_ratio": mode_ratio,
        "runtime_sec_mean": round(mu_run,2) if mu_run is not None else None,
        "runtime_sec_std": round(sd_run,2) if sd_run is not None else None,
        "loudness_lufs_mean": round(mu_lufs,2) if mu_lufs is not None else -10.5,
        "loudness_lufs_std": round(sd_lufs,2) if sd_lufs is not None else 1.5
      }
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"[aggregate_stats] wrote {args.out} from {len(packs)} packs")

if __name__ == "__main__":
    sys.exit(main())
