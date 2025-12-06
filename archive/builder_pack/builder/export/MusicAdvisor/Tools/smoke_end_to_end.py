#!/usr/bin/env python3
# MusicAdvisor/Tools/smoke_end_to_end.py
"""
Run an extractor-style JSON payload through the end-to-end pipeline and print/export
the final advisory JSON (HCI_v1 + Policy + TTC + Structural + Goldilocks + Axes).

Usage:
  music-advisor-smoke payload.json \
      --market 0.48 --emotional 0.67 \
      [--gate 0.60] [--cap 0.58] [--lift 6.0] [--round 3] [--export out.json]

Notes:
- Does NOT require pack.json or *.client.txt. It is for extractor payload smoke tests.
- payload.json example:

{
  "audio_axes": [0.62, 0.63, 0.61, 0.60, 0.64, 0.62],
  "ttc_sec": 14.0,
  "ttc_conf": 0.55,
  "verse_span": [10.0, 16.0],
  "chorus_span": [30.0, 36.0],
  "sr": 44100,
  "signal": [0.0, 0.0]  # optional
}
"""

from __future__ import annotations
import json
import argparse
import os
import sys
from pathlib import Path

# Ensure repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Tolerant imports for the e2e function
score_from_extractor_payload = None
try:
    from Pipeline.end_to_end import score_from_extractor_payload  # type: ignore
except Exception:
    try:
        from MusicAdvisor.Pipeline.end_to_end import score_from_extractor_payload  # type: ignore
    except Exception:
        score_from_extractor_payload = None  # type: ignore

# Tolerant imports for the host Policy
HostPolicy = None
try:
    from music_advisor.host.policy import Policy as HostPolicy  # type: ignore
except Exception:
    try:
        from Host.policy import Policy as HostPolicy  # type: ignore
    except Exception:
        HostPolicy = None  # type: ignore


def _round_floats(obj, n: int):
    if isinstance(obj, float):
        return round(obj, n)
    if isinstance(obj, dict):
        return {k: _round_floats(v, n) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v, n) for v in obj]
    return obj


def main():
    if score_from_extractor_payload is None:
        raise SystemExit("Pipeline.end_to_end.score_from_extractor_payload is unavailable.")

    p = argparse.ArgumentParser(description="Smoke: end-to-end from extractor-style JSON.")
    p.add_argument("payload_json", help="Path to extractor-style JSON payload")
    p.add_argument("--market", type=float, default=0.50, help="Observed market (0..1) for Goldilocks advisory")
    p.add_argument("--emotional", type=float, default=0.50, help="Observed emotional (0..1) for Goldilocks advisory")
    p.add_argument("--gate", type=float, default=None, help="Override TTC confidence gate (default from policy)")
    p.add_argument("--cap", type=float, default=None, help="Override audio cap (default from policy)")
    p.add_argument("--lift", type=float, default=None, help="Override lift window sec (default from policy)")
    p.add_argument("--round", type=int, default=None, help="Round floats in output to N decimals")
    p.add_argument("--export", type=str, default=None, help="Write output JSON to this path")
    args = p.parse_args()

    path = Path(args.payload_json)
    data = json.loads(path.read_text())

    # Build policy with optional overrides if available
    pol = HostPolicy() if HostPolicy is not None else None
    if pol is not None:
        if args.gate is not None:
            pol.ttc_conf_gate = float(args.gate)
        if args.cap is not None:
            pol.cap_audio = float(args.cap)
        if args.lift is not None:
            pol.lift_window_sec = float(args.lift)

    out = score_from_extractor_payload(
        raw=data,
        observed_market=args.market,
        observed_emotional=args.emotional,
        host_policy=pol,
    )

    if args.round is not None:
        out = _round_floats(out, args.round)

    txt = json.dumps(out, indent=2)
    if args.export:
        Path(args.export).write_text(txt, encoding="utf-8")
    else:
        print(txt)


if __name__ == "__main__":
    main()
