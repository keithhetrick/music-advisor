#!/usr/bin/env python3
"""
Merge a .client.json with its .hci.json to produce a chat-ready payload.

Usage:
  python tools/merge_client_payload.py --client /path/to/track.client.json --hci /path/to/track.hci.json --out /tmp/track.chat.json

If --out is omitted, writes alongside the client file with suffix ".chat.json".
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


HCI_FIELDS = [
    "HCI_v1_final_score",
    "HCI_v1_score",
    "HCI_v1_score_raw",
    "HCI_audio_v2",
    "HCI_v1_final_tier",
    "HCI_v1_metric_kind",
    "HCI_v1_is_hit_predictor",
    "HCI_v1_interpretation",
    "HCI_v1_notes",
    "HCI_v1_debug",
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_payload(client: Dict[str, Any], hci: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(client)
    if "audio_axes" not in merged and hci.get("axes"):
        merged["audio_axes"] = hci["axes"]
    for key in HCI_FIELDS:
        if key in hci and merged.get(key) is None:
            merged[key] = hci[key]
    if hci.get("historical_echo_v1") and not merged.get("historical_echo_v1"):
        merged["historical_echo_v1"] = hci["historical_echo_v1"]
    return merged


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge client + HCI JSON into a chat-ready payload.")
    ap.add_argument("--client", required=True, help="Path to .client.json")
    ap.add_argument("--hci", required=True, help="Path to .hci.json")
    ap.add_argument("--out", help="Output path (default: <client>.chat.json)")
    args = ap.parse_args()

    client_path = Path(args.client)
    hci_path = Path(args.hci)
    out_path = Path(args.out) if args.out else client_path.with_suffix(".chat.json")

    client = load_json(client_path)
    hci = load_json(hci_path)
    merged = merge_payload(client, hci)
    out_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"[merge] wrote chat-ready payload -> {out_path}")


if __name__ == "__main__":
    main()
