#!/usr/bin/env python3
# tools/ma_wip_build_payload.py
"""
Build a client-ready /audio import payload for a WIP track using:
  - <stem>.features.json  (from ma_audio_features.py)
  - <stem>.hci.json       (from ma_hci_from_features.py)

Outputs:
  - <stem>.client.txt   (full block to paste into Music Advisor client)
  - optionally <stem>.client.json (raw payload only, if requested)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict
from tools import names

TEMPLATE = """# Music Advisor — Paste below into {label}
# STRUCTURE_POLICY: mode=optional | reliable=false | use_ttc=false | use_exposures=false
# GOLDILOCKS_POLICY: active=true | priors={{'Market': 0.5, 'Emotional': 0.5}} | caps={{'Market': 0.58, 'Emotional': 0.58}}
# HCI_POLICY: HCI_v1.score is computed locally by MusicAdvisor and MUST be treated as canonical.
/audio import {payload}
/advisor ingest
/advisor run full
/advisor export summary
"""


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, help="Path to <stem>.features.json")
    ap.add_argument("--hci", required=True, help="Path to <stem>.hci.json")
    ap.add_argument(
        "--region",
        default="US",
        help="Region tag for payload (default: US)",
    )
    ap.add_argument(
        "--profile",
        default="Pop",
        help="Market profile tag (default: Pop)",
    )
    ap.add_argument(
        "--audio-name",
        default=None,
        help=(
            "Optional override for audio_name "
            "(default: stem from source_audio basename)"
        ),
    )
    ap.add_argument(
        "--out",
        required=True,
        help=f"Output .{names.CLIENT_TOKEN}.txt path (e.g. features_output/.../<stem>.{names.CLIENT_TOKEN}.txt)",
    )
    ap.add_argument(
        "--json-out",
        required=False,
        help=f"Optional .{names.CLIENT_TOKEN}.json output (payload only, no shell commands)",
    )
    args = ap.parse_args()

    feats = load_json(args.features)
    hci_blob = load_json(args.hci)

    # source_audio in features is typically original file path or basename
    source_audio = feats.get("source_audio") or ""
    source_basename = os.path.basename(source_audio) if source_audio else ""
    if not source_basename and "audio_name" in hci_blob:
        source_basename = hci_blob["audio_name"]

    stem = args.audio_name if args.audio_name else os.path.splitext(source_basename)[0]

    # Build features_full payload
    features_full = {
        "tempo_bpm": feats.get("tempo_bpm"),
        "key": feats.get("key"),
        "mode": feats.get("mode"),
        "duration_sec": feats.get("duration_sec"),
        "loudness_LUFS": feats.get("loudness_LUFS"),
        "energy": feats.get("energy"),
        "danceability": feats.get("danceability"),
        "valence": feats.get("valence"),
    }

    # Audio axes + HCI from hci_blob
    audio_axes = hci_blob.get("audio_axes", [])
    hci_v1 = hci_blob.get("HCI_v1", {})

    payload: Dict[str, Any] = {
        "region": args.region,
        "profile": args.profile,
        "generated_by": "automator_wip_pipeline",
        "audio_name": stem,
        "inputs": {
            "paths": {
                "source_audio": source_basename or f"{stem}.wav",
            },
            "merged_features_present": True,
            "lyric_axis_present": False,
            "internal_features_present": True,
        },
        "features_full": features_full,
        "audio_axes": audio_axes,
        "HCI_v1": hci_v1,
    }

    # Optional baseline metadata if present in hci_blob
    if "MARKET_NORMS_baseline_id" in hci_blob:
        payload["MARKET_NORMS_baseline_id"] = hci_blob["MARKET_NORMS_baseline_id"]
    if "region" in hci_blob and "profile" in hci_blob:
        payload.setdefault("baseline_region", hci_blob.get("region"))
        payload.setdefault("baseline_profile", hci_blob.get("profile"))

    # Render text template for the client
    payload_json = json.dumps(payload, ensure_ascii=False)
    client_txt = TEMPLATE.format(payload=payload_json, label=names.client_header_label())

    out_path = Path(args.client_out) if args.client_out else Path(args.out)
    out_path.write_text(client_txt)
    print(f"[ma_wip_build_payload] wrote {out_path}")

    if args.json_out:
        json_out_path = Path(args.json_out)
        json_out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"[ma_wip_build_payload] wrote {json_out_path}")
    if args.json_out or args.client_json_out:
        cjson_path = Path(args.client_json_out) if args.client_json_out else out_path.with_suffix(names.client_json_suffix())
        cjson_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"[ma_wip_build_payload] wrote {cjson_path}")


if __name__ == "__main__":
    main()
