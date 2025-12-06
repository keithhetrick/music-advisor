#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Music Advisor — Calibration Aggregator
Build MARKET_NORMS from calibration packs, robust to folder naming differences.

Usage:
  python tools/ma_calibrate.py \
    --packs-glob "features_output/**/*.pack.json" \
    --out "datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json" \
    --region US --profile Pop

Notes:
- We infer the "anchor family" from the parent directory of the audio file
  used to generate the pack (e.g., calibration/audio/08_indie_singer_songwriter).
- Slug normalization + synonyms make folder spelling variants safe.
"""

import argparse, glob, json, math, statistics, sys
from pathlib import Path

# --------- helpers

def _safe_mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return float(statistics.mean(xs)) if xs else None

def _safe_std(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return float(statistics.pstdev(xs)) if len(xs) > 1 else 0.0

def _slugify_family(s: str) -> str:
    """
    Normalize a folder name into a canonical anchor family slug.
    - lowercase
    - replace hyphens with underscores
    - coalesce multiple underscores
    - specific fixes: 'singerwriter' -> 'singer_songwriter'
    """
    s = (s or "").strip().lower()
    s = s.replace("-", "_")
    while "__" in s:
        s = s.replace("__", "_")
    s = s.replace("singerwriter", "singer_songwriter")
    return s

# folder synonym map → canonical family
FAMILY_SYNONYMS = {
    "08_indie_singerwriter": "08_indie_singer_songwriter",
}

def _canonical_family_from_path(pack_path: Path) -> str:
    """
    Resolve canonical family based on expected layout:
      calibration/audio/<index>_<family_slug>/...
    Fall back: just slugify the parent name.
    """
    # Try to find ".../calibration/audio/<family>/" in its path, if present
    parts = [p for p in pack_path.as_posix().split("/") if p]
    fam = None
    for i, token in enumerate(parts):
        if token == "audio" and i+1 < len(parts):
            fam = parts[i+1]
            break
    if fam is None:
        # fallback: parent folder of the original audio (if recorded in pack)
        fam = pack_path.parent.name

    fam = FAMILY_SYNONYMS.get(fam, fam)
    return _slugify_family(fam)

def _accumulate_key_counts(key_counts, key):
    if not isinstance(key, str) or not key:
        return
    # normalize flats/sharps to simple ascii (Db/Eb/Gb/Ab/Bb, A..G, etc.)
    k = key.replace("♭", "b").replace("♯", "#")
    # map enharmonic D# -> Eb for key distribution consistency (optional)
    ENH = {"D#":"Eb", "G#":"Ab", "A#":"Bb", "C#":"Db", "F#":"Gb"}
    k = ENH.get(k, k)
    key_counts[k] = key_counts.get(k, 0) + 1

# --------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs-glob", required=True, help="Glob to calibration .pack.json files")
    ap.add_argument("--region", default="US")
    ap.add_argument("--profile", default="Pop")
    ap.add_argument("--out", required=True, help="Where to write the baseline bundle JSON")
    args = ap.parse_args()

    pack_files = sorted(glob.glob(args.packs_glob, recursive=True))
    if not pack_files:
        print(f"[calibrate] No pack files matched glob: {args.packs_glob}", file=sys.stderr)
        return 2

    tempos, runtimes, modes = [], [], []
    key_counts = {}

    per_family_counts = {}  # debug/inspection

    for p in pack_files:
        P = Path(p)
        try:
            d = json.loads(P.read_text())
        except Exception as e:
            print(f"[calibrate] skip {P}: {e}", file=sys.stderr)
            continue

        # features may be in root or in nested fields (we standardized to pack_writer)
        feats = d.get("features_full") or d.get("features") or {}
        bpm = feats.get("bpm") or feats.get("tempo_bpm")
        dur = feats.get("duration_sec") or feats.get("runtime_sec")
        mode = feats.get("mode")
        key  = feats.get("key")

        fam = _canonical_family_from_path(P)

        if bpm: tempos.append(float(bpm))
        if dur: runtimes.append(float(dur))
        if isinstance(mode, str) and mode in ("major", "minor"):
            modes.append(mode)
        _accumulate_key_counts(key_counts, key)

        per_family_counts[fam] = per_family_counts.get(fam, 0) + 1

    tempo_mean = _safe_mean(tempos)
    tempo_std  = _safe_std(tempos)
    runtime_mean = _safe_mean(runtimes)
    runtime_std  = _safe_std(runtimes)

    mode_major = modes.count("major")
    mode_minor = modes.count("minor")
    mode_total = max(1, mode_major + mode_minor)
    mode_ratio = {"major": round(mode_major/mode_total, 2),
                  "minor": round(mode_minor/mode_total, 2)}

    # normalize key distribution to probabilities
    total_keys = sum(key_counts.values()) or 1
    key_distribution = {k: round(v/total_keys, 2) for k, v in sorted(key_counts.items())}

    norms = {
        "tempo_bpm_mean": round(tempo_mean, 2) if tempo_mean is not None else None,
        "tempo_bpm_std": round(tempo_std, 2) if tempo_std is not None else None,
        "tempo_band_pref": ["100–109", "110–119", "120–129"],  # keep existing preference bands
        "key_distribution": key_distribution,
        "mode_ratio": mode_ratio,
        "runtime_sec_mean": round(runtime_mean, 2) if runtime_mean is not None else None,
        "runtime_sec_std": round(runtime_std, 2) if runtime_std is not None else None,
    }

    out = {
        "id": f"{args.region}_{args.profile}_Cal_Baseline_2025Q4.json",
        "REGION": args.region,
        "PROFILE": args.profile,
        "MARKET_NORMS": norms,
        "provenance": {
            "source": "calibration/packs",
            "packs_glob": args.packs_glob,
            "families_seen": per_family_counts
        }
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"[calibrate] wrote {args.out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
