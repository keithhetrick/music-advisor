#!/usr/bin/env python3
"""
Validate feature JSONs against the host contract schema by wrapping them
into a minimal payload with audio_axes + TTC stub.

Usage:
    python scripts/validate_features_against_contract.py path/to/*.features.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from jsonschema import Draft7Validator

SCHEMA_PATH = Path("vendor/MusicAdvisor_BuilderPack/contracts/schema/audiotools_payload_v0.3.5.schema.json")


def build_payload(features: Dict[str, Any]) -> Dict[str, Any]:
    """Map a feature JSON into the contract shape required by the host."""
    duration = features.get("duration_sec") or features.get("duration") or 0.0
    # Best-effort mapping of normalized axes; fill missing slots with 0.5.
    axes: List[float] = []
    for key in ("energy", "danceability", "valence"):
        val = features.get(key)
        try:
            axes.append(float(val))
        except Exception:
            axes.append(0.5)
    # Fill remaining slots to length 6.
    while len(axes) < 6:
        axes.append(0.5)

    payload = {
        "duration_sec": float(duration),
        "audio_axes": axes[:6],
        "TTC": {
            "seconds": None,
            "confidence": None,
            "lift_db": None,
            "dropped": ["chorus_lift"],
            "source": "absent",
        },
    }
    # Optional tempo block for completeness (not required by schema).
    if "tempo_bpm" in features:
        payload["tempo"] = {"bpm": features.get("tempo_bpm"), "band_10s": None}
    return payload


def validate_paths(paths: List[Path]) -> int:
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft7Validator(schema)
    failed = 0
    for p in paths:
        data = json.loads(p.read_text())
        payload = build_payload(data)
        errors = list(validator.iter_errors(payload))
        if errors:
            failed += 1
            print(f"[FAIL] {p} -> {len(errors)} errors")
            for e in errors[:5]:
                print("   -", list(e.path), e.message)
        else:
            print(f"[OK]   {p}")
    return failed


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate feature JSONs against host contract schema.")
    ap.add_argument("paths", nargs="+", help="Feature JSON files (e.g., *.features.json)")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    paths = [Path(p) for p in args.paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        print(f"Missing files: {missing}", file=sys.stderr)
        return 1
    failed = validate_paths(paths)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
