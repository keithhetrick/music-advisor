from __future__ import annotations
import argparse
import json
from pathlib import Path
from ma_audio_engine.analyzers.audio_core import analyze_basic_features
from ma_audio_engine.always_present import coerce_payload_shape

def _round_payload(obj, nd: int):
    if nd is None:
        return obj
    if isinstance(obj, dict):
        return {k: _round_payload(v, nd) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_payload(v, nd) for v in obj]
    if isinstance(obj, float):
        return round(obj, nd)
    return obj

def main() -> None:
    ap = argparse.ArgumentParser(description="MusicAdvisor Audio Extractor")
    ap.add_argument("--audio", required=True, help="Path to audio file")
    ap.add_argument("--out", required=True, help="Output JSON path")
    ap.add_argument("--sr", type=int, default=44100)
    ap.add_argument("--round", type=int, default=3, dest="nd")
    ap.add_argument("--axes", type=str, default=None, help="Comma list of 6 floats to override audio_axes")
    args = ap.parse_args()

    feats = analyze_basic_features(args.audio, sr=args.sr, round_ndigits=args.nd)

    if args.axes:
        parts = [p.strip() for p in args.axes.split(",") if p.strip()]
        override = []
        for p in parts:
            try:
                override.append(float(p))
            except Exception:
                pass
        if override:
            feats["audio_axes"] = override

    payload = coerce_payload_shape(feats)
    payload = _round_payload(payload, args.nd)

    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[ma-extract] wrote {args.out}")

if __name__ == "__main__":
    main()
