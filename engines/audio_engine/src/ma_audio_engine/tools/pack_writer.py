#!/usr/bin/env python3
"""
Pack writer (dict-based) used by pipeline_api and CLI.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from ma_audio_engine.adapters.logging_adapter import make_logger

_log = make_logger("pack_writer", redact=os.environ.get("LOG_REDACT", "1") == "1")


def build_pack(
    merged: Dict[str, Any],
    audio_name: str,
    anchor: str,
    lyric_axis: Optional[Dict[str, Any]] = None,
    features_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    features_meta = features_meta or {}
    prov = merged.get("provenance", {})
    if features_meta.get("provenance"):
        prov = {**prov, **features_meta.get("provenance", {})}
    feature_meta = {
        "source_hash": features_meta.get("source_hash", ""),
        "config_fingerprint": features_meta.get("config_fingerprint", ""),
        "pipeline_version": features_meta.get("pipeline_version", ""),
        "generated_utc": features_meta.get("generated_utc"),
        "sidecar_status": features_meta.get("sidecar_status"),
        "sidecar_attempts": features_meta.get("sidecar_attempts"),
        "sidecar_timeout_seconds": features_meta.get("sidecar_timeout_seconds"),
    }
    pack = {
        "audio_name": audio_name,
        "region": merged.get("region", "US"),
        "profile": anchor,
        "inputs": {
            "paths": {"source_audio": merged.get("source_audio", "")},
            "merged_features_present": True,
            "lyric_axis_present": lyric_axis is not None,
            "internal_features_present": True,
        },
        "features": {
            "tempo_bpm": merged.get("tempo_bpm"),
            "key": merged.get("key"),
            "mode": merged.get("mode"),
            "duration_sec": merged.get("duration_sec"),
            "runtime_sec": merged.get("runtime_sec"),
            "loudness_LUFS": merged.get("loudness_LUFS"),
            "energy": merged.get("energy"),
            "danceability": merged.get("danceability"),
            "valence": merged.get("valence"),
        },
        "features_full": {
            "bpm": merged.get("tempo_bpm"),
            "mode": merged.get("mode"),
            "key": merged.get("key"),
            "duration_sec": merged.get("duration_sec"),
            "runtime_sec": merged.get("runtime_sec"),
            "loudness_lufs": merged.get("loudness_LUFS"),
            "energy": merged.get("energy"),
            "danceability": merged.get("danceability"),
            "valence": merged.get("valence"),
        },
        "feature_pipeline_meta": feature_meta,
        "provenance": prov,
    }
    if lyric_axis:
        pack["lyric_axis"] = lyric_axis
    ttc_fields = {
        "ttc_seconds_first_chorus": merged.get("ttc_seconds_first_chorus"),
        "ttc_bars_first_chorus": merged.get("ttc_bars_first_chorus"),
        "ttc_source": merged.get("ttc_source"),
        "ttc_estimation_method": merged.get("ttc_estimation_method"),
        "ttc_confidence": merged.get("ttc_confidence"),
        "bpm_used": merged.get("bpm_used"),
    }
    if any(v is not None for v in ttc_fields.values()):
        pack["ttc"] = {k: v for k, v in ttc_fields.items() if v is not None}
        pack.setdefault("features", {}).update(
            {
                "ttc_seconds_first_chorus": ttc_fields.get("ttc_seconds_first_chorus"),
                "ttc_bars_first_chorus": ttc_fields.get("ttc_bars_first_chorus"),
            }
        )
        pack.setdefault("features_full", {}).update(
            {
                "ttc_seconds_first_chorus": ttc_fields.get("ttc_seconds_first_chorus"),
                "ttc_bars_first_chorus": ttc_fields.get("ttc_bars_first_chorus"),
            }
        )
    return pack


def build_client_helper_payload(pack: Dict[str, Any]) -> Dict[str, Any]:
    src_audio = pack["inputs"]["paths"].get("source_audio", "")
    if isinstance(src_audio, str):
        src_audio_basename = os.path.basename(src_audio)
    else:
        src_audio_basename = src_audio
    prov = pack.get("provenance") or {}
    runtime_sec = (
        pack.get("features", {}).get("runtime_sec")
        or pack.get("features", {}).get("duration_sec")
        or pack.get("features_full", {}).get("duration_sec")
    )
    duration_sec = runtime_sec if runtime_sec is not None else pack.get("features_full", {}).get("duration_sec")
    payload = {
        "region": pack.get("region"),
        "profile": pack.get("profile"),
        "generated_by": "pack_writer",
        "audio_name": pack.get("audio_name"),
        "inputs": {
            "paths": {"source_audio": src_audio_basename},
            "merged_features_present": pack.get("inputs", {}).get("merged_features_present"),
            "lyric_axis_present": pack.get("inputs", {}).get("lyric_axis_present"),
            "internal_features_present": pack.get("inputs", {}).get("internal_features_present"),
        },
        "features": {
            "tempo_bpm": pack.get("features", {}).get("tempo_bpm"),
            "key": pack.get("features", {}).get("key"),
            "mode": pack.get("features", {}).get("mode"),
            "duration_sec": duration_sec,
            "runtime_sec": runtime_sec,
            "loudness_LUFS": pack.get("features_full", {}).get("loudness_lufs"),
            "energy": pack.get("features_full", {}).get("energy"),
            "danceability": pack.get("features_full", {}).get("danceability"),
            "valence": pack.get("features_full", {}).get("valence"),
        },
        "features_full": {
            "bpm": pack.get("features_full", {}).get("bpm"),
            "mode": pack.get("features_full", {}).get("mode"),
            "key": pack.get("features_full", {}).get("key"),
            "duration_sec": duration_sec,
            "runtime_sec": runtime_sec,
            "loudness_lufs": pack.get("features_full", {}).get("loudness_lufs"),
            "energy": pack.get("features_full", {}).get("energy"),
            "danceability": pack.get("features_full", {}).get("danceability"),
            "valence": pack.get("features_full", {}).get("valence"),
        },
        "feature_pipeline_meta": {
            "source_hash": pack.get("feature_pipeline_meta", {}).get("source_hash", ""),
            "config_fingerprint": pack.get("feature_pipeline_meta", {}).get("config_fingerprint", ""),
            "pipeline_version": pack.get("feature_pipeline_meta", {}).get("pipeline_version", ""),
            "generated_utc": pack.get("feature_pipeline_meta", {}).get("generated_utc"),
            "sidecar_status": pack.get("feature_pipeline_meta", {}).get("sidecar_status"),
            "sidecar_attempts": pack.get("feature_pipeline_meta", {}).get("sidecar_attempts"),
            "sidecar_timeout_seconds": pack.get("feature_pipeline_meta", {}).get("sidecar_timeout_seconds"),
        },
        "historical_echo_meta": None,
        "historical_echo_v1": None,
    }
    if "ttc" in pack:
        ttc_block = pack["ttc"]
        payload["ttc"] = ttc_block
        payload.setdefault("features", {}).update(
            {
                "ttc_seconds_first_chorus": ttc_block.get("ttc_seconds_first_chorus"),
                "ttc_bars_first_chorus": ttc_block.get("ttc_bars_first_chorus"),
            }
        )
        payload.setdefault("features_full", {}).update(
            {
                "ttc_seconds_first_chorus": ttc_block.get("ttc_seconds_first_chorus"),
                "ttc_bars_first_chorus": ttc_block.get("ttc_bars_first_chorus"),
            }
        )
    if prov:
        payload["provenance"] = prov
    payload["helper_text_version"] = "v6.3"
    payload["helper_text_id"] = _log.sha
    payload["helper_text_date"] = os.environ.get("PACK_HELPER_DATE") or Path(__file__).stat().st_mtime
    payload["helper_text_policies"] = {
        "text_area_min_lines": 5,
        "explicit_words": [],
        "included_sections": ["meta", "hci", "summary", "spotcheck"],
    }
    return payload


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def main_cli(args: argparse.Namespace) -> int:
    merged = _load_json(args.merged)
    audio_name = Path(merged.get("source_audio") or args.merged).stem
    lyric_axis = _load_json(args.lyric_axis) if args.lyric_axis else None
    features_meta = _load_json(args.features) if args.features else None
    pack = build_pack(merged, audio_name=audio_name, anchor=args.anchor, lyric_axis=lyric_axis, features_meta=features_meta)
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not args.no_pack:
        out_pack = out_dir / f"{audio_name}.pack.json"
        out_pack.write_text(json.dumps(pack, indent=2))
    client_payload = build_client_helper_payload(pack)
    if args.client_json:
        Path(args.client_json).write_text(json.dumps(client_payload, indent=2))
    if args.client_txt:
        Path(args.client_txt).write_text(json.dumps(client_payload, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Write pack/client helpers from merged features.json")
    ap.add_argument("--merged", required=True, help="merged.json from equilibrium_merge")
    ap.add_argument("--features", default=None, help="(optional) features.json for pipeline meta/provenance")
    ap.add_argument("--lyric-axis", dest="lyric_axis", default=None, help="(optional) lyric_axis.json")
    ap.add_argument("--out-dir", required=True, help="output directory")
    ap.add_argument("--anchor", default="00_core_modern")
    ap.add_argument("--client-json", default=None, help="optional client helper JSON path")
    ap.add_argument("--client-txt", default=None, help="optional client helper text path")
    ap.add_argument("--no-pack", action="store_true", help="skip writing pack.json")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    rc = main_cli(args)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
