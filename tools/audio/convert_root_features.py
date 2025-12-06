#!/usr/bin/env python3
"""
Convert ROOT-style ma_audio_features.py output into pipeline-style features.

Usage:
    python tools/convert_root_features.py \
        --in  root_style.features.json \
        --out pipeline_style.features.json

This is a best-effort mapping intended for legacy files. For benchmark/hitlist
calibration, prefer re-extracting from audio with tools/ma_audio_features.py.
"""

import argparse
import json
import os
from typing import Any, Dict


def convert_one(data: Dict[str, Any]) -> Dict[str, Any]:
    if "flat" not in data or "features_full" not in data:
        raise ValueError("Input JSON does not look like ROOT-style output (missing flat/features_full).")

    flat = data.get("flat", {})
    full = data.get("features_full", {})

    tempo_bpm = flat.get("tempo_bpm", full.get("bpm", 0.0))
    duration_sec = flat.get("runtime_sec", full.get("duration_sec", 0.0))
    loudness = flat.get("loudness_lufs_integrated", full.get("loudness_lufs", 0.0))
    key_root = flat.get("key_root", full.get("key"))
    key_mode = flat.get("key_mode", full.get("mode", "unknown"))

    energy = flat.get("energy", full.get("energy"))
    dance = flat.get("danceability", full.get("danceability"))
    valence = flat.get("valence", full.get("valence"))

    out: Dict[str, Any] = {
        "source_audio": data.get("path"),
        "sample_rate": None,  # unknown in root-format; left as null
        "duration_sec": float(duration_sec or 0.0),
        "tempo_bpm": float(tempo_bpm or 0.0),
        "key": key_root,
        "mode": key_mode if key_mode in ("major", "minor") else "unknown",
        "loudness_LUFS": float(loudness or 0.0),
        "energy": float(energy) if energy is not None else None,
        "danceability": float(dance) if dance is not None else None,
        "valence": float(valence) if valence is not None else None,
    }
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Convert ROOT-style features.json to pipeline-style.")
    parser.add_argument("--in", dest="input_path", required=True, help="ROOT-style .features.json")
    parser.add_argument("--out", dest="output_path", required=True, help="Output pipeline-style .features.json")
    args = parser.parse_args(argv)

    with open(args.input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        converted = convert_one(data)
    except Exception as e:
        print(f"[convert_root_features] ERROR: {e}")
        return 1

    os.makedirs(os.path.dirname(args.output_path) or ".", exist_ok=True)
    with open(args.output_path, "w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2, ensure_ascii=False)

    print(
        f"[convert_root_features] Converted ROOT-style -> pipeline-style:\n"
        f"  in : {args.input_path}\n"
        f"  out: {args.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
