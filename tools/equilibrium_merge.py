#!/usr/bin/env python3
"""
Lightweight merge utility for combining ma_audio_features output with optional
external enrichment. Adapterized for consistent logging and sandboxed output.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import add_log_sandbox_arg, add_log_format_arg, add_preflight_arg, apply_log_sandbox_env, apply_log_format_env, run_preflight_if_requested
from ma_audio_engine.adapters import di, load_log_settings
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from ma_audio_engine.schemas import dump_json
from shared.ma_utils import get_configured_logger
from shared.ma_utils.schema_utils import lint_merged_payload

ESSENTIAL_KEYS = ["duration_sec", "tempo_bpm", "key", "mode", "loudness_LUFS"]


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def pick(src: Dict[str, Any], keys: Iterable[str]) -> Optional[Any]:
    for k in keys:
        if k in src and src[k] is not None:
            return src[k]
    return None


def merge_features(
    internal: Dict[str, Any],
    external: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    merged["source_audio"] = os.path.basename(pick(internal, ["source_audio", "audio", "file"])) if internal else None
    merged["duration_sec"] = pick(internal, ["duration_sec", "runtime_sec", "duration"])
    merged["tempo_bpm"] = pick(internal, ["tempo_bpm", "bpm"])
    merged["key"] = pick(internal, ["key"])
    merged["mode"] = pick(internal, ["mode"])
    merged["loudness_LUFS"] = pick(internal, ["loudness_LUFS", "lufs", "LUFS"])
    merged["energy"] = pick(internal, ["energy"])
    merged["danceability"] = pick(internal, ["danceability"])
    merged["valence"] = pick(internal, ["valence"])
    if external:
        for k in ["energy", "danceability", "valence"]:
            if k in external:
                merged[k] = external[k]
    def pull_ttc(src: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        ttc: Dict[str, Any] = {}
        if not isinstance(src, dict):
            return ttc
        block = src.get("ttc") if isinstance(src.get("ttc"), dict) else src
        aliases = {
            "ttc_seconds_first_chorus": ["ttc_seconds_first_chorus", "ttc_seconds"],
            "ttc_bars_first_chorus": ["ttc_bars_first_chorus", "ttc_bars"],
        }
        for dest, keys in aliases.items():
            val = pick(block, keys)
            if val is not None:
                ttc[dest] = val
        if "ttc_source" in block:
            ttc["ttc_source"] = block["ttc_source"]
        elif "source" in block:
            ttc["ttc_source"] = block["source"]
        if "ttc_estimation_method" in block:
            ttc["ttc_estimation_method"] = block["ttc_estimation_method"]
        elif "estimation_method" in block:
            ttc["ttc_estimation_method"] = block["estimation_method"]
        if "ttc_confidence" in block:
            ttc["ttc_confidence"] = block["ttc_confidence"]
        if "bpm_used" in block:
            ttc["bpm_used"] = block["bpm_used"]
        if "ttc_bpm_used" in block:
            ttc["bpm_used"] = block["ttc_bpm_used"]
        return ttc

    # TTC fields prefer external overrides if present.
    ttc_merged: Dict[str, Any] = {}
    for src in (internal, external):
        if src:
            ttc_merged.update({k: v for k, v in pull_ttc(src).items() if v is not None})
    merged.update(ttc_merged)
    return merged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal", required=True, help="features.json from ma_audio_features")
    ap.add_argument("--external", default=None, help="optional external enrichments")
    ap.add_argument("--out", required=True, help="output merged.json")
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
        help="Exit non-zero if lint warnings are found in merged output.",
    )
    add_log_sandbox_arg(ap)
    add_log_format_arg(ap)
    add_preflight_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    apply_log_format_env(args)
    run_preflight_if_requested(args)
    log = get_configured_logger("equilibrium_merge", defaults={"tool": "equilibrium_merge"})

    internal = load_json(args.internal)
    external = load_json(args.external) if args.external and os.path.exists(args.external) else None

    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        log("start", {"event": "start", "tool": "equilibrium_merge", "internal": args.internal, "out": args.out})
        log_stage_start(log, "merge", internal=args.internal, external=args.external, out=args.out)

    merged = merge_features(internal, external)

    missing = [k for k in ESSENTIAL_KEYS if merged.get(k) is None]
    if missing:
        log(f"WARN: missing keys: {missing}")

    lint_warnings = lint_merged_payload(merged)
    status = "ok"
    if lint_warnings:
        log(f"[equilibrium_merge] lint warnings: {lint_warnings}")
        if args.strict:
            status = "error"
    if status == "error":
        if os.getenv("LOG_JSON") == "1":
            log_stage_end(log, "merge", status="error", warnings=lint_warnings)
        return 1

    dump_json(Path(args.out), merged)
    log(f"Wrote merged features -> {args.out}")
    if os.getenv("LOG_JSON") == "1":
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        log_stage_end(
            log,
            "merge",
            status=status,
            internal=args.internal,
            external=args.external,
            out=args.out,
            duration_ms=duration_ms,
            missing_count=len(missing),
            warnings=lint_warnings,
        )
        log("end", {"event": "end", "tool": "equilibrium_merge", "internal": args.internal, "out": args.out, "status": status, "duration_ms": duration_ms, "warnings": lint_warnings})
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
