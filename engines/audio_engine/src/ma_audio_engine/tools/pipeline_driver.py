#!/usr/bin/env python3
"""
Unified pipeline driver used by Automator and CLI flows.

What it does:
- Runs the canonical chain: features (with sidecar) -> merge -> pack/client -> optional engine audit + HCI/client.rich/neighbors.
- Produces timestamped artifacts plus compatibility copies so legacy consumers continue to work.

Configuration surface:
- Defaults from ma_config.pipeline (profiles, sidecar timeout).
- Env overrides: HCI_BUILDER_PROFILE, NEIGHBORS_PROFILE, SIDECAR_TIMEOUT_SECONDS, PIPELINE_PY (Python), LOG_JSON passthrough.
- Optional JSON config: --config <path> to override profiles/timeout.

Outputs:
- Timestamped: <stem>_<ts>.features.json, .sidecar.json, .merged.json, .pack.json (full only).
- Compatibility: <stem>.client.txt/.json/.rich.txt, <stem>.hci.json, <stem>.neighbors.json, run_summary.json.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from ma_config.paths import get_repo_root, get_features_output_root, get_historical_echo_db_path
from ma_config.pipeline import (
    HCI_BUILDER_PROFILE_DEFAULT,
    NEIGHBORS_PROFILE_DEFAULT,
    SIDECAR_TIMEOUT_DEFAULT,
)
from security import paths as sec_paths
from security import subprocess as sec_subprocess
from security.config import CONFIG as SEC_CONFIG
from security import files as sec_files


def _run(cmd: list[str], cwd: Optional[Path] = None, env: Optional[dict] = None, timeout: Optional[int] = None) -> int:
    try:
        completed = sec_subprocess.run_safe(
            cmd,
            cwd=cwd,
            env=env,
            timeout=timeout if timeout is not None else SEC_CONFIG.subprocess_timeout,
            allow_roots=SEC_CONFIG.allowed_binary_roots,
            check=False,
        )
        return completed.returncode
    except Exception:
        return 1


def load_pipeline_config(config_path: Optional[Path]) -> dict:
    cfg = {
        "hci_builder_profile": HCI_BUILDER_PROFILE_DEFAULT,
        "neighbors_profile": NEIGHBORS_PROFILE_DEFAULT,
        "sidecar_timeout_seconds": SIDECAR_TIMEOUT_DEFAULT,
    }
    if not config_path:
        return cfg
    try:
        data = json.loads(Path(config_path).read_text())
    except Exception:
        return cfg
    for key in ("hci_builder_profile", "neighbors_profile", "sidecar_timeout_seconds"):
        if key in data:
            cfg[key] = data[key]
    return cfg


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run the end-to-end pipeline (features -> merge -> pack/HCI).")
    ap.add_argument("audio", help="path to input audio")
    ap.add_argument("--config", default=None, help="optional JSON config for pipeline defaults")
    ap.add_argument("--out-dir", default=None, help="explicit output directory (else features_output/<date>/<stem>)")
    ap.add_argument("--skip-pack", action="store_true", help="skip pack writing (client helpers still possible)")
    ap.add_argument("--skip-neighbors", action="store_true", help="skip neighbors in pack/client helpers")
    ap.add_argument("--skip-lyrics", action="store_true", help="skip lyric axis")
    ap.add_argument("--anchor", default="00_core_modern", help="anchor/role name")
    ap.add_argument("--features", default=None, help="precomputed features.json (skip feature extraction)")
    ap.add_argument("--sidecar", default=None, help="precomputed sidecar.json (skip tempo sidecar)")
    ap.add_argument("--merged", default=None, help="precomputed merged.json (skip merge)")
    ap.add_argument("--log-json", action="store_true", help="emit JSON logs")
    ap.add_argument("--dry-run", action="store_true", help="print planned commands and exit")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    repo = get_repo_root()
    cfg_path = Path(args.config).expanduser().resolve() if args.config else None
    cfg = load_pipeline_config(cfg_path)

    env = os.environ.copy()
    env.setdefault("LOG_REDACT", "1")
    env.setdefault("SIDECAR_TIMEOUT_SECONDS", str(cfg["sidecar_timeout_seconds"]))
    env.setdefault("HCI_BUILDER_PROFILE", cfg["hci_builder_profile"])
    env.setdefault("NEIGHBORS_PROFILE", cfg["neighbors_profile"])
    env.setdefault("HISTORICAL_ECHO_DB", str(get_historical_echo_db_path()))

    audio = Path(args.audio).expanduser().resolve()
    if not audio.exists() or not audio.is_file():
        print(f"[ERR] audio not found: {audio}", file=os.sys.stderr)
        return 66
    if audio.is_symlink():
        print(f"[ERR] audio must not be a symlink: {audio}", file=os.sys.stderr)
        return 66
    try:
        sec_files.ensure_allowed_extension(audio, SEC_CONFIG.allowed_exts)
    except Exception as exc:
        print(f"[ERR] disallowed extension: {exc}", file=os.sys.stderr)
        return 65

    stem = audio.stem
    date_prefix = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else get_features_output_root() / "smoke" / date_prefix / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    features_json = out_dir / f"{stem}.features.json"
    sidecar_json = out_dir / f"{stem}.sidecar.json"
    merged_json = out_dir / f"{stem}.merged.json"

    # 1) features (with sidecar)
    if not args.features:
        cmd = ["ma-audio-features", "--audio", str(audio), "--out", str(features_json), "--tempo-backend", "sidecar", "--require-sidecar", "--tempo-sidecar-json-out", str(sidecar_json)]
        if args.log_json:
            env["LOG_JSON"] = "1"
        if _run(cmd, cwd=repo, env=env) != 0:
            return 1
    else:
        features_json = Path(args.features).expanduser().resolve()

    # 2) merge
    if not args.merged:
        cmd = ["equilibrium-merge", "--internal", str(features_json), "--out", str(merged_json)]
        if _run(cmd, cwd=repo, env=env) != 0:
            return 1
    else:
        merged_json = Path(args.merged).expanduser().resolve()

    # 3) pack + client helpers
    if not args.skip_pack:
        pack_cmd = [
            "pack-writer",
            "--merged",
            str(merged_json),
            "--out-dir",
            str(out_dir),
            "--anchor",
            args.anchor,
            "--no-pack" if args.skip_pack else "",
        ]
        pack_cmd = [c for c in pack_cmd if c]
        if args.skip_neighbors:
            pack_cmd.append("--no-neighbors")
        if args.skip_lyrics:
            pack_cmd.append("--no-lyrics")
        if _run(pack_cmd, cwd=repo, env=env) != 0:
            return 1

    print(f"[pipeline-driver] done -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
