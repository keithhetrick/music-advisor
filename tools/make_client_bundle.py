#!/usr/bin/env python3
"""
Bundle an /audio output and a recommendation JSON into one client-ready JSON.

Usage:
  python tools/make_client_bundle.py --audio-json path/to/file.merged.json \
    --recommendation path/to/file.recommendation.json \
    --out /tmp/client_bundle.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Bundle audio + recommendation into one JSON.")
    ap.add_argument("--audio-json", required=True, help="Path to merged or features JSON.")
    ap.add_argument("--recommendation", required=True, help="Path to recommendation JSON.")
    ap.add_argument("--out", required=True, help="Output path.")
    args = ap.parse_args()

    audio = json.loads(Path(args.audio_json).read_text())
    rec = json.loads(Path(args.recommendation).read_text())

    bundle = {"audio": audio, "recommendation": rec}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, indent=2))
    print(f"[make_client_bundle] wrote -> {out_path}")


if __name__ == "__main__":
    main()
