#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from typing import Sequence, Optional, Tuple

from music_advisor.host.policy import Policy
from music_advisor.host.kpi import hci_v1
from music_advisor.host.run_card import emit_run_card

# Use your capitalized implementation
from ma_hf_audiotools.Segmentation import SegmentationResult, apply_ttc_gate_and_lift

def parse_axes(txt: str) -> list[float]:
    try:
        vals = json.loads(txt)
        if isinstance(vals, list) and len(vals) == 6:
            vals = [float(x) for x in vals]
            assert all(0.0 <= x <= 1.0 for x in vals)
            return vals
    except Exception as e:
        raise SystemExit(f"Invalid --axes JSON (need 6 floats in [0,1]): {e}")
    raise SystemExit("Invalid --axes: provide JSON list of 6 floats in [0,1]")

def load_signal_from_json(path: Optional[str]) -> tuple[list[float], int]:
    """
    Minimal stand-in for audio. Expects a JSON file: {"sr": 44100, "signal": [floats...]}
    You can craft tiny arrays for testing; no need for real audio here.
    """
    if not path:
        # default tiny signal
        return [0.0]*44100, 44100
    with open(path, "r", encoding="utf-8") as f:
        j = json.load(f)
    sr = int(j.get("sr", 44100))
    sig = [float(x) for x in j.get("signal", [])]
    if not sig:
        sig = [0.0]*sr
    return sig, sr

def main():
    ap = argparse.ArgumentParser(description="Smoke: TTC gate + HCI @ host boundary")
    ap.add_argument("--axes", required=True, help='JSON list of 6 floats in [0,1], e.g. "[0.62,0.63,0.61,0.60,0.64,0.62]"')
    ap.add_argument("--ttc-sec", type=float, default=None, help="TTC seconds (optional)")
    ap.add_argument("--ttc-conf", type=float, default=None, help="TTC confidence [0,1] (optional)")
    ap.add_argument("--verse", type=str, default=None, help='JSON pair for verse span, e.g. "[10.0,16.0]"')
    ap.add_argument("--chorus", type=str, default=None, help='JSON pair for chorus span, e.g. "[30.0,36.0]"')
    ap.add_argument("--signal-json", type=str, default=None, help='Optional JSON file with {"sr":44100,"signal":[...]}')
    ap.add_argument("--track-id", type=str, default="smoke")
    ap.add_argument("--profile", type=str, default="US_Pop_2025")
    ap.add_argument("--emit-card", action="store_true")
    ap.add_argument("--card-dir", type=str, default="out/run_cards")
    ap.add_argument("--ttc-gate", type=float, default=None, help="Override TTC confidence gate")
    ap.add_argument("--lift-window", type=float, default=None, help="Override chorus lift window seconds")
    args = ap.parse_args()

    axes = parse_axes(args.axes)

    sig, sr = load_signal_from_json(args.signal_json)

    verse = json.loads(args.verse) if args.verse else None
    chorus = json.loads(args.chorus) if args.chorus else None
    if verse is not None:
        verse = (float(verse[0]), float(verse[1]))
    if chorus is not None:
        chorus = (float(chorus[0]), float(chorus[1]))

    pol = Policy()
    if args.ttc_gate is not None:
        pol.ttc_conf_gate = float(args.ttc_gate)
    if args.lift_window is not None:
        pol.lift_window_sec = float(args.lift_window)

    seg = SegmentationResult(
        ttc_seconds=args.ttc_sec,
        ttc_confidence=args.ttc_conf,
        verse_span=verse,
        chorus_span=chorus,
    )

    gate = apply_ttc_gate_and_lift(sig, sr, seg, pol)
    hci = hci_v1(axes, pol)

    out = {
        "HCI_v1": hci,
        "policy": {
            "cap_audio": pol.cap_audio,
            "ttc_conf_gate": pol.ttc_conf_gate,
            "lift_window_sec": pol.lift_window_sec,
        },
        "gate": gate,
    }

    if args.emit_card:
        os.makedirs(args.card_dir, exist_ok=True)
        emit_run_card(
            out_dir=args.card_dir,
            track_id=args.track_id,
            policy=pol,
            profile=args.profile,
            ttc_seconds=gate["ttc_seconds"],
            ttc_confidence=gate["ttc_confidence"],
            lift_db=gate["lift_db"],
            dropped_features=gate["drop_features"],
            notes={"HCI": hci, "smoke": True},
        )
        out["run_card_path"] = os.path.join(args.card_dir, f"{args.track_id}_run_card.json")

    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
