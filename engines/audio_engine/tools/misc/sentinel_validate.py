"""
Legacy sentinel/pack builder utility relocated under audio_engine.tools.misc.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

# Baseline + advisory (NON-SCORING)
from ma_audio_engine.host.baseline_loader import load_baseline
from ma_audio_engine.host.baseline_normalizer import summarize_market_fit

def _read_json(p: str | Path) -> dict:
    p = Path(p)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}

def build_pack(merged: dict, lyric_axis: dict, internal_features: dict, region: str, profile: str) -> dict:
    # Minimal stable pack surface (augment as needed)
    pack = {
        "region": region,
        "profile": profile,
        "generated_by": "pack_writer",
        "inputs": {
            "merged_features": bool(merged),
            "lyric_axis": bool(lyric_axis),
            "internal_features": bool(internal_features),
        },
        "features": {
            "tempo_bpm": merged.get("tempo_bpm") or internal_features.get("tempo_bpm"),
            "key": merged.get("key") or internal_features.get("key"),
            "mode": merged.get("mode") or internal_features.get("mode"),
            "runtime_sec": merged.get("duration_sec") or internal_features.get("duration_sec"),
        },
        "lyric_axis": lyric_axis or {},
        # Advisors & baseline will be added below
    }

    # Attach Baseline
    baseline = load_baseline(region=region, profile=profile)
    if baseline is None:
        pack["Baseline"] = {
            "id": None,
            "note": "Baseline cohort not found.",
            "MARKET_NORMS": {}
        }
    else:
        pack["Baseline"] = {
            "id": baseline.get("id"),
            "MARKET_NORMS": baseline.get("MARKET_NORMS", {})
        }

    # NON-SCORING advisory (guarded by env flag)
    if os.getenv("MA_DISABLE_NORMS_ADVISORY") != "1":
        try:
            norms = pack["Baseline"].get("MARKET_NORMS", {})
            if norms:
                pack["Baseline"].setdefault("advisory", {}).update(summarize_market_fit(norms))
        except Exception as e:
            pack["Baseline"]["advisory_error"] = str(e)

    return pack

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--merged", required=True, help="Merged features JSON (internal + optional external)")
    p.add_argument("--lyric-axis", required=True, help="Lyric intelligence (HLM/HLI derivation) JSON")
    p.add_argument("--internal-features", required=True, help="Internal audio features JSON")
    p.add_argument("--region", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    merged = _read_json(args.merged)
    lyric_axis = _read_json(args.lyric_axis)
    internal = _read_json(args.internal_features)

    pack = build_pack(merged, lyric_axis, internal, args.region, args.profile)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(pack, ensure_ascii=False, indent=2))
    print(f"[pack_writer] wrote {outp}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
