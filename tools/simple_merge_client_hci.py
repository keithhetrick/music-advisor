#!/usr/bin/env python3
"""
Simple merger to bundle client payload + HCI payload into one JSON artifact.

Usage:
  python tools/simple_merge_client_hci.py --client path/to/*.client.json --hci path/to/*.hci.json --out merged.json

Notes:
- Does not alter the .client.rich.txt.
- Minimal dependency surface: only stdlib.
- Output structure: {"client": <client_json>, "hci": <hci_json>}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text())


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge client + HCI JSON into one artifact.")
    ap.add_argument("--client", required=True, help="Path to *.client.json")
    ap.add_argument("--hci", required=True, help="Path to *.hci.json")
    ap.add_argument("--out", required=True, help="Output merged JSON path")
    args = ap.parse_args()

    client = load_json(Path(args.client))
    hci = load_json(Path(args.hci))
    merged = {"client": client, "hci": hci}

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, indent=2))
    print(f"[merged] wrote -> {out_path}")


if __name__ == "__main__":
    main()
