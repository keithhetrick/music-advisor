#!/usr/bin/env python3
"""
TTC sidecar CLI (stub) — placeholder for time-to-chorus detection.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env, make_logger  # type: ignore[import-not-found]  # noqa: E402
from ma_lyrics_engine.schema import ensure_schema  # type: ignore[import-not-found]  # noqa: E402
from ma_ttc_engine.detect_choruses import estimate_ttc  # type: ignore[import-not-found]  # noqa: E402
from ma_ttc_engine.ttc_features import build_ttc_features_stub, write_ttc_features  # type: ignore[import-not-found]  # noqa: E402
from ma_config.profiles import (  # type: ignore[import-not-found]  # noqa: E402
    DEFAULT_TTC_CONFIG_PATH,
    DEFAULT_TTC_PROFILE,
    resolve_profile_config,
)
from ma_config.paths import get_lyric_intel_db_path  # type: ignore[import-not-found]  # noqa: E402


def run_estimate(args, log) -> None:
    db_path = Path(args.db).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)

    # Derive structure labels and tempo/duration if available in DB.
    structure = None
    tempo = None
    duration = None
    if args.song_id:
        cur = conn.cursor()
        cur.execute("SELECT tempo_bpm, duration_sec, section_pattern FROM features_song WHERE song_id=?", (args.song_id,))
        row = cur.fetchone()
        if row:
            tempo = row[0]
            duration = row[1]
            pattern = row[2] or ""
            structure = [tok for tok in pattern.split("-") if tok]
        if not structure:
            cur.execute("SELECT label FROM sections WHERE lyrics_id LIKE ? ORDER BY start_line ASC", (f"{args.song_id}%",))
            sec_rows = cur.fetchall()
            if sec_rows:
                structure = [r[0] for r in sec_rows]
    if structure is None and args.section_pattern:
        structure = [tok for tok in args.section_pattern.split("-") if tok]

    # Load TTC config if provided
    ttc_profile, profile_path, cfg = resolve_profile_config(
        cli_profile=getattr(args, "ttc_profile", None),
        cli_config=getattr(args, "ttc_config", None),
        env_profile_var="LYRIC_TTC_PROFILE",
        env_config_var="LYRIC_TTC_CONFIG",
        default_profile=DEFAULT_TTC_PROFILE,
        default_config_path=DEFAULT_TTC_CONFIG_PATH,
        log=log,
    )
    beats_per_bar = 4.0
    seconds_per_section = args.seconds_per_section
    if cfg:
        seconds_per_section = float(cfg.get("seconds_per_section_fallback", seconds_per_section))
        beats_per_bar = float(cfg.get("beats_per_bar", beats_per_bar))
    ttc = estimate_ttc(
        structure_labels=structure,
        tempo_bpm=tempo,
        duration_sec=duration,
        seconds_per_section_fallback=seconds_per_section,
        beats_per_bar=beats_per_bar,
    )
    features = build_ttc_features_stub()
    if args.song_id:
        write_ttc_features(
            conn,
            args.song_id,
            ttc,
            profile=ttc_profile,
            estimation_method=ttc.get("estimation_method", "ttc_rule_based_v1"),
            ttc_confidence=ttc.get("ttc_confidence", "low"),
        )
    payload = {"song_id": args.song_id, "ttc": ttc, "features": features, "profile": ttc_profile, "config_path": str(profile_path)}
    out_json = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")
        log(f"[INFO] Wrote TTC stub payload: {args.out}")
    else:
        print(out_json)
    conn.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Time-To-Chorus sidecar (stub).")
    add_log_sandbox_arg(ap)
    sub = ap.add_subparsers(dest="cmd")

    est = sub.add_parser("estimate", help="Estimate TTC (stub implementation).")
    est.add_argument("--db", default=str(get_lyric_intel_db_path()), help="SQLite DB path (for writing TTC features).")
    est.add_argument("--song-id", help="Optional song identifier for metadata.", default=None)
    est.add_argument("--section-pattern", help="Optional section pattern string (e.g., V-P-C-V-C).")
    est.add_argument("--seconds-per-section", type=float, default=12.0, help="Fallback seconds per section when duration missing.")
    est.add_argument("--ttc-config", help="Optional TTC profile JSON to load heuristics (overrides env LYRIC_TTC_CONFIG).")
    est.add_argument("--ttc-profile", help="TTC profile label (overrides env LYRIC_TTC_PROFILE). May also be a JSON path for legacy usage.")
    est.add_argument("--out", help="Optional output JSON path.")
    est.add_argument("--timeout-seconds", type=float, default=None, help="Optional timeout (env TTC_TIMEOUT_SECONDS).")
    defaults = vars(ap.parse_args([]))
    args = ap.parse_args()
    if not getattr(args, "cmd", None):
        ap.print_help()
        raise SystemExit(0)
    args = _apply_env_overrides(args, defaults)
    return args


def _apply_env_overrides(args: argparse.Namespace, defaults: dict) -> argparse.Namespace:
    """
    Allow env JSON to override defaults when CLI flags are not provided.
    Env: TTC_OPTS='{\"seconds_per_section\":10,\"ttc_profile\":\"fast\"}'
    CLI takes precedence; env only applies when the arg is still at its default.
    """
    raw = os.getenv("TTC_OPTS")
    if not raw:
        return args
    try:
        data = json.loads(raw)
    except Exception:
        return args
    for key, val in data.items():
        if key in defaults and getattr(args, key, None) == defaults[key]:
            setattr(args, key, val)
    return args


def main() -> None:
    args = parse_args()
    apply_log_sandbox_env(args)
    log = make_logger("ttc_sidecar")
    if args.timeout_seconds is None and os.getenv("TTC_TIMEOUT_SECONDS"):
        try:
            args.timeout_seconds = float(os.getenv("TTC_TIMEOUT_SECONDS"))
        except Exception:
            args.timeout_seconds = None
    if args.cmd == "estimate":
        run_estimate(args, log)
    else:
        raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
