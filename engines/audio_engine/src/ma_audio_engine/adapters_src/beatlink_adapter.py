#!/usr/bin/env python3
"""
BeatLink adapter shim: produces a minimal external tempo/key payload.

Usage:
- python adapters/beatlink_adapter.py --audio path/to/audio --out /tmp/beatlink.json
- If a sibling .beat.json exists next to the audio, merge it into the payload.

Outputs a JSON of the form:
{
  "external_vendor": "BeatLink",
  "model_version": "beatlink.0.1",
  "tempo_bpm_external": null,
  "key_signature_external": null,
  "beatgrid": {"first_beat_ms": null, "grid_locked": false},
  "confidence": {"tempo": 0.0, "key": 0.0},
  "ts": "<utc iso>"
  ...plus any merged fields from the optional .beat.json
}
"""
import argparse
import json
import pathlib
import sys
import time

__all__ = [
    "main",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="BeatLink adapter shim")
    ap.add_argument("--audio", required=True, help="Path to source audio (used to locate optional .beat.json sidecar).")
    ap.add_argument("--out", required=True, help="Destination JSON path for BeatLink payload.")
    args = ap.parse_args()

    payload = {
        "external_vendor": "BeatLink",
        "model_version": "beatlink.0.1",
        "tempo_bpm_external": None,
        "key_signature_external": None,
        "beatgrid": {"first_beat_ms": None, "grid_locked": False},
        "confidence": {"tempo": 0.0, "key": 0.0},
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    sidecar = pathlib.Path(args.audio).with_suffix(".beat.json")
    if sidecar.exists():
        try:
            ext = json.loads(sidecar.read_text())
            if isinstance(ext, dict):
                payload.update(ext)
        except Exception as exc:  # noqa: BLE001
            print(f"[beatlink] sidecar read failed: {exc}", file=sys.stderr)

    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2))
    print(f"[beatlink] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
