#!/usr/bin/env python3
"""
Validate that a .features.json file has the canonical pipeline shape.

Intended usage:
    python tools/validate_features_shape.py path/to/file.features.json

Returns exit code 0 if valid, 1 if invalid. Prints a clear diagnostic.
"""

import json
import sys
from typing import List

REQUIRED_KEYS: List[str] = [
    "source_audio",
    "sample_rate",
    "duration_sec",
    "tempo_bpm",
    "key",
    "mode",
    "loudness_LUFS",
    "energy",
    "danceability",
    "valence",
]


def validate(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[validate_features_shape] ERROR: cannot read {path}: {e}", file=sys.stderr)
        return False

    if isinstance(data, dict) and "flat" in data and "features_full" in data:
        print(
            f"[validate_features_shape] {path}: looks like ROOT-style nested output "
            f"(flat/features_full). This is NOT valid for HCI pipeline. "
            f"Re-extract using tools/ma_audio_features.py or convert.",
            file=sys.stderr,
        )
        return False

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        print(
            f"[validate_features_shape] {path}: missing required keys: {', '.join(missing)}",
            file=sys.stderr,
        )
        return False

    print(f"[validate_features_shape] {path}: OK (pipeline features shape).")
    return True


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("Usage: validate_features_shape.py file1.features.json [file2 ...]", file=sys.stderr)
        return 1

    ok = True
    for path in argv:
        if not validate(path):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
