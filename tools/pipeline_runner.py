#!/usr/bin/env python3
"""
Thin CLI that exercises the pipeline_api (features -> merge -> pack -> client+HCI merge).

Purpose:
- Developer helper to run the in-process pipeline without shell scripts.
- Emits features, sidecar, merged, and client rich/json artifacts; skips pack writing and full HCI.

Side effects:
- Writes multiple JSON/TXT outputs into --out-dir.
- Uses pipeline_api (in-process), so no external subprocesses beyond what the API invokes.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools import pipeline_api  # noqa: E402
from tools import names
from tools.ma_merge_client_and_hci import load_tempo_overlay_block, load_key_overlay_block
from tools import tempo_norms_sidecar as tns
from tools import key_norms_sidecar as kns


def main() -> int:
    ap = argparse.ArgumentParser(description="Run pipeline_api end-to-end for a single audio file.")
    ap.add_argument("--audio", required=True, help="Path to audio file.")
    ap.add_argument("--out-dir", required=True, help="Output directory root.")
    ap.add_argument("--require-sidecar", action="store_true", help="Require sidecar tempo/key (if available).")
    ap.add_argument("--strict", action="store_true", help="Exit non-zero on lint warnings.")
    ap.add_argument("--lane-id", default="tier1__2015_2024", help="Lane ID for tempo norms sidecar (default: tier1__2015_2024).")
    ap.add_argument("--tempo-db", default=None, help="Optional lyric_intel DB path for tempo norms (defaults to tempo_norms_sidecar default).")
    ap.add_argument("--bin-width", type=float, default=2.0, help="Bin width for tempo norms (default: 2 BPM).")
    ap.add_argument("--key-lane-id", default="tier1__2015_2024", help="Lane ID for key norms sidecar (default: tier1__2015_2024).")
    ap.add_argument("--key-db", default=None, help="Optional historical_echo DB path for key norms (defaults to get_historical_echo_db_path).")
    args = ap.parse_args()

    audio = Path(args.audio).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = audio.stem
    features_out = out_dir / f"{stem}.features.json"
    sidecar_out = out_dir / f"{stem}.sidecar.json"
    merged_out = out_dir / f"{stem}.merged.json"
    client_json_out = out_dir / f"{stem}{names.client_json_suffix()}"
    client_txt_out = out_dir / f"{stem}{names.client_rich_suffix()}"

    feats = pipeline_api.run_features(str(audio), tempo_sidecar_json_out=str(sidecar_out), require_sidecar=args.require_sidecar)
    features_out.write_text(json.dumps(feats, indent=2))

    merged, merge_warns = pipeline_api.run_merge(feats, None)
    merged_out.write_text(json.dumps(merged, indent=2))

    pack = pipeline_api.run_pack(
        merged,
        out_dir,
        write_pack=False,
        client_json=client_json_out,
        client_txt=client_txt_out,
    )

    # Tempo norms sidecar (best effort)
    tempo_norms_out = out_dir / f"{stem}{names.tempo_norms_sidecar_suffix()}"
    try:
        song_bpm = merged.get("tempo_bpm") or feats.get("tempo_bpm")
        if song_bpm:
            db_path = Path(args.tempo_db).expanduser().resolve() if args.tempo_db else tns.get_lyric_intel_db_path()
            conn = sqlite3.connect(str(db_path))
            tns.ensure_schema(conn)
            lane_bpms = tns.load_lane_bpms(conn, args.lane_id)
            if lane_bpms:
                payload = tns.build_sidecar_payload(args.lane_id, float(song_bpm), args.bin_width, lane_bpms)
                tempo_norms_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            conn.close()
    except Exception as exc:  # noqa: BLE001
        # Non-fatal; continue pipeline if tempo norms fail
        print(f"[pipeline_runner] tempo_norms_sidecar skipped: {exc}")

    # Key norms sidecar (best effort)
    key_norms_out = out_dir / f"{stem}{names.key_norms_sidecar_suffix()}"
    try:
        song_key = merged.get("key") or feats.get("key")
        song_mode = merged.get("mode") or feats.get("mode")
        if song_key and song_mode:
            db_path = Path(args.key_db).expanduser().resolve() if args.key_db else kns.get_historical_echo_db_path()
            conn = sqlite3.connect(str(db_path))
            lane_keys = kns.load_lane_keys(conn, args.key_lane_id)
            if lane_keys:
                song_key_obj = kns._normalize_key_pair(song_key, song_mode)  # type: ignore[attr-defined]
                if song_key_obj:
                    payload = kns.build_sidecar_payload(args.key_lane_id, song_key_obj, lane_keys)
                    key_norms_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[pipeline_runner] key_norms_sidecar skipped: {exc}")

    # Minimal HCI stub (since full HCI run is out of scope for this helper)
    hci_stub = {"HCI_v1_final_score": merged.get("tempo_bpm", 0), "HCI_v1_role": "unknown"}
    tempo_overlay_block = load_tempo_overlay_block(pack.get("audio_name"), out_dir)
    key_overlay_block = load_key_overlay_block(pack.get("audio_name"), out_dir)
    client_merged, rich_text, merge_warns2 = pipeline_api.run_merge_client_hci(
        pack,
        hci_stub,
        tempo_overlay_block=tempo_overlay_block,
        key_overlay_block=key_overlay_block,
    )
    client_txt_out.write_text(rich_text)

    warns = merge_warns + merge_warns2
    if warns and args.strict:
        print(f"[pipeline_runner] strict mode: warnings: {warns}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
