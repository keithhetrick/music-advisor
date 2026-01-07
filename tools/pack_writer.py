#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import pathlib
import datetime
import time
import hashlib
from typing import Any, Dict
import subprocess
import importlib

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import add_log_sandbox_arg, add_log_format_arg, add_preflight_arg, apply_log_sandbox_env, apply_log_format_env, run_preflight_if_requested
from ma_audio_engine.adapters import make_logger
from ma_audio_engine.adapters import utc_now_iso
from ma_audio_engine.adapters import di, load_log_settings, load_runtime_settings
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from ma_audio_engine.schemas import dump_json
from tools import names
from tools.schema_utils import lint_merged_payload, lint_pack_payload

LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
_log = make_logger("pack_writer", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)


def load_json(p: str | os.PathLike[str]) -> Dict[str, Any]:
    with open(p, "r") as f:
        return json.load(f)


def write_json(p: str | os.PathLike[str], obj: Dict[str, Any]) -> None:
    pathlib.Path(os.path.dirname(p)).mkdir(parents=True, exist_ok=True)
    dump_json(pathlib.Path(p), obj)


def safe_stem(path: str) -> str:
    base = os.path.basename(path)
    return os.path.splitext(base)[0]


def _git_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=pathlib.Path(__file__).resolve().parent.parent)
        return out.decode().strip()
    except Exception:
        return "unknown"


def _dep_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {}
    for mod in ("numpy", "scipy", "librosa", "essentia", "madmom"):
        try:
            versions[mod] = importlib.import_module(mod).__version__  # type: ignore[attr-defined]
        except Exception:
            versions[mod] = "missing"
    return versions

def build_pack(merged: Dict[str, Any], audio_name: str, anchor: str, lyric_axis: Dict[str, Any] | None = None, features_meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    prov = merged.get("provenance") or {}
    feat_prov = (features_meta or {}).get("provenance") or {}
    prov.update({k: v for k, v in feat_prov.items() if v is not None})
    # Attempt to pull source_hash / track_id from merged; otherwise derive from source_audio string
    source_hash = merged.get("source_hash") or (features_meta or {}).get("source_hash")
    track_id = prov.get("track_id") or (source_hash[:12] if isinstance(source_hash, str) else None)
    if not track_id and merged.get("source_audio"):
        track_id = hashlib.sha1(str(merged["source_audio"]).encode()).hexdigest()[:12]
    if not prov:
        prov = {
            "git_sha": _git_sha(),
            "deps": _dep_versions(),
        }
    if track_id:
        prov["track_id"] = track_id
    prov.setdefault("git_sha", _git_sha())
    prov.setdefault("deps", _dep_versions())
    prov.setdefault("calibration_version", os.getenv("HCI_CAL_VERSION", "unknown"))
    prov.setdefault("calibration_date", os.getenv("HCI_CAL_DATE", utc_now_iso()))

    def _pick_meta(key: str) -> Any:
        for src in (merged, features_meta):
            if isinstance(src, dict) and src.get(key) is not None:
                return src[key]
        return None

    meta_src = merged.get("feature_pipeline_meta") or (features_meta or {}).get("feature_pipeline_meta") or {}
    meta_src = dict(meta_src) if isinstance(meta_src, dict) else {}
    meta_src.setdefault("source_hash", _pick_meta("source_hash") or "")
    meta_src.setdefault("config_fingerprint", _pick_meta("config_fingerprint") or "")
    meta_src.setdefault("pipeline_version", _pick_meta("pipeline_version") or "")
    meta_src.setdefault("generated_utc", _pick_meta("generated_utc") or _pick_meta("processed_utc"))
    meta_src.setdefault("sidecar_status", _pick_meta("sidecar_status"))
    meta_src.setdefault("sidecar_attempts", _pick_meta("sidecar_attempts"))
    meta_src.setdefault("sidecar_timeout_seconds", _pick_meta("sidecar_timeout_seconds"))
    meta_src.setdefault("tempo_backend", _pick_meta("tempo_backend"))
    meta_src.setdefault("tempo_backend_detail", _pick_meta("tempo_backend_detail"))
    if isinstance(_pick_meta("tempo_backend_meta"), dict):
        meta_src.setdefault("tempo_backend_meta", _pick_meta("tempo_backend_meta"))
    meta_src.setdefault("tempo_backend_source", _pick_meta("tempo_backend_source"))
    meta_src.setdefault("qa_gate", _pick_meta("qa_gate"))

    # Prefer canonical source_hash derived from meta for downstream provenance.
    if isinstance(meta_src.get("source_hash"), str):
        source_hash = meta_src["source_hash"]
    if not track_id and isinstance(source_hash, str):
        track_id = source_hash[:12]
    if track_id:
        prov["track_id"] = track_id
    pack = {
      "region": "US",
      "profile": "Pop",
      "generated_by": "pack_writer",
      "audio_name": audio_name,
      "inputs": {
        "paths": {
          "source_audio": merged.get("source_audio", "")
        },
        "merged_features_present": True,
        "lyric_axis_present": bool(lyric_axis),
        "internal_features_present": True,
      },
      "features": {
        "tempo_bpm": round(float(merged["tempo_bpm"]), 2),
        "key": merged["key"],
        "mode": merged["mode"],
        "runtime_sec": round(float(merged["duration_sec"]), 2),
        "loudness_LUFS": float(merged["loudness_LUFS"]),
        "energy": merged.get("energy"),
        "danceability": merged.get("danceability"),
        "valence": merged.get("valence"),
      },
      "features_full": {
        "bpm": round(float(merged["tempo_bpm"]), 2),
        "mode": merged["mode"],
        "key": merged["key"],
        "duration_sec": round(float(merged["duration_sec"]), 2),
        "loudness_lufs": float(merged["loudness_LUFS"]),
        "energy": merged.get("energy"),
        "danceability": merged.get("danceability"),
        "valence": merged.get("valence"),
      },
      "anchor": anchor,
      "provenance": prov,
      "feature_pipeline_meta": {
        "source_hash": meta_src.get("source_hash", ""),
        "config_fingerprint": meta_src.get("config_fingerprint", ""),
        "pipeline_version": meta_src.get("pipeline_version", ""),
        "generated_utc": meta_src.get("generated_utc"),
        "sidecar_status": meta_src.get("sidecar_status"),
        "sidecar_attempts": meta_src.get("sidecar_attempts"),
        "sidecar_timeout_seconds": meta_src.get("sidecar_timeout_seconds"),
        "tempo_backend": meta_src.get("tempo_backend"),
        "tempo_backend_detail": meta_src.get("tempo_backend_detail"),
        "qa_gate": meta_src.get("qa_gate"),
      },
    }
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
        pack["features"]["ttc_seconds_first_chorus"] = ttc_fields["ttc_seconds_first_chorus"]
        pack["features"]["ttc_bars_first_chorus"] = ttc_fields["ttc_bars_first_chorus"]
        pack["features_full"]["ttc_seconds_first_chorus"] = ttc_fields["ttc_seconds_first_chorus"]
        pack["features_full"]["ttc_bars_first_chorus"] = ttc_fields["ttc_bars_first_chorus"]
    if lyric_axis:
        pack["lyric_axis"] = lyric_axis
    return pack

def build_client_helper_payload(pack: Dict[str, Any]) -> Dict[str, Any]:
    src_audio = pack["inputs"]["paths"]["source_audio"]
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
    if runtime_sec is None and pack.get("features_full", {}).get("duration_sec") is not None:
        runtime_sec = pack["features_full"]["duration_sec"]
    if runtime_sec is None:
        runtime_sec = pack.get("duration_sec") or 0
    duration_sec = runtime_sec if runtime_sec is not None else pack.get("features_full", {}).get("duration_sec") or 0
    meta_src = dict(pack.get("feature_pipeline_meta") or {})
    payload = {
      "region": pack["region"],
      "profile": pack["profile"],
      "generated_by": "pack_writer",
      "audio_name": pack["audio_name"],
      "inputs": {
        "paths": {
          "source_audio": src_audio_basename,
        },
        "merged_features_present": pack["inputs"]["merged_features_present"],
        "lyric_axis_present": pack["inputs"]["lyric_axis_present"],
        "internal_features_present": pack["inputs"]["internal_features_present"],
      },
      "features": {
        "tempo_bpm": pack["features"]["tempo_bpm"],
        "key": pack["features"]["key"],
        "mode": pack["features"]["mode"],
        "duration_sec": duration_sec,
        "runtime_sec": runtime_sec,
        "loudness_LUFS": pack["features_full"]["loudness_lufs"],
        "energy": pack["features_full"]["energy"],
        "danceability": pack["features_full"]["danceability"],
        "valence": pack["features_full"]["valence"],
      },
      "features_full": {
        "bpm": pack["features_full"]["bpm"],
        "mode": pack["features_full"]["mode"],
        "key": pack["features_full"]["key"],
        "duration_sec": duration_sec,
        "runtime_sec": runtime_sec,
        "loudness_lufs": pack["features_full"]["loudness_lufs"],
        "energy": pack["features_full"]["energy"],
        "danceability": pack["features_full"]["danceability"],
        "valence": pack["features_full"]["valence"],
      },
      "feature_pipeline_meta": {
        "source_hash": meta_src.get("source_hash") or pack.get("inputs", {}).get("paths", {}).get("source_audio", ""),
        "config_fingerprint": meta_src.get("config_fingerprint", ""),
        "pipeline_version": meta_src.get("pipeline_version", ""),
        "generated_utc": meta_src.get("generated_utc"),
        "sidecar_status": meta_src.get("sidecar_status"),
        "sidecar_attempts": meta_src.get("sidecar_attempts"),
        "sidecar_timeout_seconds": meta_src.get("sidecar_timeout_seconds"),
        "tempo_backend": meta_src.get("tempo_backend"),
        "tempo_backend_detail": meta_src.get("tempo_backend_detail"),
        "tempo_backend_meta": meta_src.get("tempo_backend_meta"),
        "tempo_backend_source": meta_src.get("tempo_backend_source"),
        "qa_gate": meta_src.get("qa_gate"),
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
    # Always emit provenance to surface version defaults
    if prov:
        payload["provenance"] = prov
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description="Write *.pack.json and optional client helpers from merged features.")
    ap.add_argument("--merged", required=True, help="merged.json from equilibrium_merge")
    ap.add_argument("--features", default=None, help="(optional) raw features.json, for provenance")
    ap.add_argument("--lyrics", default=None, help="(optional) lyrics.json")
    ap.add_argument("--lyric-axis", dest="lyric_axis", default=None, help="(optional) lyric_axis.json")
    ap.add_argument("--beatlink", default=None, help="(optional) beatlink.json")
    ap.add_argument("--out-dir", required=True, help="output directory")
    ap.add_argument("--anchor", default="00_core_modern")
    ap.add_argument("--client-txt", default=None, help=f"optional {names.CLIENT_TOKEN} helper .txt")
    ap.add_argument("--client-json", default=None, help=f"optional {names.CLIENT_TOKEN} helper .json")
    ap.add_argument(
        "--no-pack",
        action="store_true",
        help="skip writing *.pack.json (useful when only client helpers are needed)",
    )
    ap.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    ap.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if lint warnings are found.",
    )
    add_log_sandbox_arg(ap)
    add_log_format_arg(ap)
    add_preflight_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    apply_log_format_env(args)
    run_preflight_if_requested(args)
    # Align runtime/config defaults across CLIs
    _ = load_runtime_settings(args)
    settings = load_log_settings(args)
    redact_flag = settings.log_redact or LOG_REDACT
    redact_values = settings.log_redact_values or LOG_REDACT_VALUES
    global _log
    _log = di.make_logger("pack_writer", structured=os.getenv("LOG_JSON") == "1", defaults={"tool": "pack_writer"}, redact=redact_flag, secrets=redact_values)

    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        log_stage_start(
            _log,
            "pack_writer",
            merged=args.merged,
            out_dir=args.out_dir,
            wants_pack=not args.no_pack,
            wants_client_txt=bool(args.client_txt),
            wants_client_json=bool(args.client_json),
        )

    merged = load_json(args.merged)
    features_meta = None
    feat_path = args.features
    if not feat_path:
        candidate = pathlib.Path(args.merged).with_suffix(".features.json")
        if candidate.exists():
            feat_path = str(candidate)
        else:
            alt = candidate.with_name(candidate.name.replace(".merged", ".features"))
            if alt.exists():
                feat_path = str(alt)
    if feat_path and os.path.exists(feat_path):
        try:
            features_meta = load_json(feat_path)
        except Exception:
            features_meta = None

    # Guard against empties for the most essential fields
    essentials = ["duration_sec", "tempo_bpm", "key", "mode", "loudness_LUFS"]
    missing = [k for k in essentials if merged.get(k) is None]
    if missing:
        _log(
            "[pack_writer] aborting: missing essentials "
            + json.dumps({k: merged.get(k) for k in essentials}, indent=2)
        )
        if os.getenv("LOG_JSON") == "1":
            log_stage_end(_log, "pack_writer", status="error", reason="missing_essentials", missing=missing)
        sys.exit(1)

    lint_merged = lint_merged_payload(merged)
    audio_name = safe_stem(merged.get("source_audio") or os.path.basename(args.merged))
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    lyric_axis_payload = None
    if args.lyric_axis and os.path.exists(args.lyric_axis):
        try:
            lyric_axis_payload = load_json(args.lyric_axis)
        except Exception:
            lyric_axis_payload = {"flags": {"lyrics_missing": True}}

    pack = build_pack(merged, audio_name=audio_name, anchor=args.anchor, lyric_axis=lyric_axis_payload, features_meta=features_meta)

    if args.lyric_axis and os.path.exists(args.lyric_axis):
        try:
            pack["lyric_axis"] = load_json(args.lyric_axis)
        except Exception:
            pack["lyric_axis"] = {"flags": {"lyrics_missing": True}}

    lint_pack = lint_pack_payload(pack)
    out_pack = None
    if not args.no_pack:
        out_pack = os.path.join(args.out_dir, f"{audio_name}_{ts}.pack.json")
        write_json(out_pack, pack)

    # Client helper
    if args.client_txt:
        helper_payload = build_client_helper_payload(pack)
        header = "# CLIENT PAYLOAD — for advisor_host ingestion\n"
        lines = [
            header + "/audio import " + json.dumps(helper_payload, ensure_ascii=False),
            "",
            "/advisor ingest",
            "/advisor run full",
            "/advisor export summary",
        ]
        content = "\n".join(lines) + "\n"
        os.makedirs(os.path.dirname(args.client_txt), exist_ok=True)
        with open(args.client_txt, "w", encoding="utf-8") as f:
            f.write(content)

    if args.client_json:
        client_helper = build_client_helper_payload(pack)
        client_helper["track_title"] = audio_name
        write_json(args.client_json, client_helper)

    now = utc_now_iso()
    if os.getenv("LOG_JSON") == "1":
        log_stage_start(
            _log,
            "pack_writer",
            out_dir=args.out_dir,
            wrote_pack=bool(out_pack),
            wrote_client_txt=bool(args.client_txt),
            wrote_client_json=bool(args.client_json),
        )
    else:
        if out_pack:
            _log(f"[pack_writer] wrote pack -> {out_pack} @ {now}")
        if args.client_txt:
            _log(f"[pack_writer] wrote {names.CLIENT_TOKEN}.txt -> {args.client_txt} @ {now}")
        if args.client_json:
            _log(f"[pack_writer] wrote {names.CLIENT_TOKEN}.json -> {args.client_json} @ {now}")

    warnings = lint_merged + lint_pack
    if warnings:
        _log(f"[pack_writer] lint warnings: {warnings}")
        if args.strict:
            if os.getenv("LOG_JSON") == "1":
                log_stage_end(
                    _log,
                    "pack_writer",
                    status="error",
                    out_dir=args.out_dir,
                    warnings=warnings,
                )
            raise SystemExit("strict mode: lint warnings present")

    if os.getenv("LOG_JSON") == "1":
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        log_stage_end(
            _log,
            "pack_writer",
            status="ok",
            out_dir=args.out_dir,
            duration_ms=duration_ms,
            wrote_pack=bool(out_pack),
            wrote_client_txt=bool(args.client_txt),
            wrote_client_json=bool(args.client_json),
            warnings=warnings,
        )
        _log("end", {"event": "end", "tool": "pack_writer", "out_dir": args.out_dir, "status": "ok", "duration_ms": duration_ms, "warnings": warnings})

if __name__ == "__main__":
    main()
