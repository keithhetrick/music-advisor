#!/usr/bin/env python3
from adapters.bootstrap import ensure_repo_root
"""
Sweep a folder of audio files with the tempo sidecar and log confidence/key metadata.

Outputs CSV with per-track sidecar backend, tempo/key, raw vs normalized confidence, and beat count.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parent.parent
ensure_repo_root()

from tools.ma_audio_features import normalize_external_confidence, TARGET_SR  # noqa: E402
from security import subprocess as sec_subprocess
from security.config import CONFIG as SEC_CONFIG


AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".aiff", ".aif", ".ogg"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run tempo sidecar across a folder and summarize confidence/key stats.")
    p.add_argument("--root", required=True, help="Root folder containing audio files.")
    p.add_argument("--out", default="sidecar_sweep.csv", help="Output CSV path (default: sidecar_sweep.csv)")
    p.add_argument(
        "--backend",
        choices=["auto", "essentia", "madmom", "librosa"],
        default="auto",
        help="Sidecar backend preference (default: auto).",
    )
    p.add_argument("--sample-rate", type=int, default=TARGET_SR, help=f"Sample rate for sidecar (default: {TARGET_SR})")
    p.add_argument("--limit", type=int, help="Optional max number of files to process.")
    p.add_argument("--verbose", action="store_true", help="Print progress details.")
    return p.parse_args()


def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg)


def run_sidecar(audio_path: Path, backend: str, sample_rate: int, verbose: bool) -> Optional[Dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="sidecar_sweep_") as tmpdir:
        out_json = Path(tmpdir) / "sidecar.json"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "tools" / "tempo_sidecar_runner.py"),
            "--audio",
            str(audio_path),
            "--out",
            str(out_json),
            "--backend",
            backend,
            "--sample-rate",
            str(sample_rate),
        ]
        if verbose:
            cmd.append("--verbose")
        try:
            completed = sec_subprocess.run_safe(
                cmd,
                allow_roots=SEC_CONFIG.allowed_binary_roots,
                timeout=SEC_CONFIG.subprocess_timeout,
                check=True,
            )
        except Exception as e:  # noqa: BLE001
            log(f"[WARN] sidecar failed for {audio_path}: {e}", True)
            return None
        if not out_json.exists():
            return None
        try:
            return json.loads(out_json.read_text())
        except Exception as e:  # noqa: BLE001
            log(f"[WARN] failed to parse sidecar JSON for {audio_path}: {e}", True)
            return None


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    if not root.exists():
        print(f"[ERR] root not found: {root}", file=sys.stderr)
        return 1

    audio_files = [p for p in root.rglob("*") if p.suffix.lower() in AUDIO_EXTS]
    audio_files.sort()
    if args.limit:
        audio_files = audio_files[: args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "audio",
                "backend",
                "tempo",
                "tempo_confidence_score_raw",
                "tempo_confidence_score_norm",
                "tempo_confidence_label",
                "key",
                "mode",
                "key_strength",
                "beats_count",
            ],
        )
        writer.writeheader()
        for idx, audio_path in enumerate(audio_files, 1):
            log(f"[{idx}/{len(audio_files)}] {audio_path}", args.verbose)
            sidecar = run_sidecar(audio_path, args.backend, args.sample_rate, args.verbose)
            if not sidecar:
                writer.writerow({"audio": str(audio_path), "backend": "error"})
                continue
            backend = sidecar.get("backend")
            tempo = sidecar.get("tempo")
            tempo_conf_raw = sidecar.get("tempo_confidence_score")
            tempo_conf_norm = normalize_external_confidence(tempo_conf_raw, backend)
            tempo_conf_label = sidecar.get("tempo_confidence")
            beats = sidecar.get("beats_sec") or []
            key = sidecar.get("key")
            mode = sidecar.get("mode")
            key_strength = sidecar.get("key_strength")
            writer.writerow(
                {
                    "audio": str(audio_path),
                    "backend": backend,
                    "tempo": tempo,
                    "tempo_confidence_score_raw": tempo_conf_raw,
                    "tempo_confidence_score_norm": tempo_conf_norm,
                    "tempo_confidence_label": tempo_conf_label,
                    "key": key,
                    "mode": mode,
                    "key_strength": key_strength,
                    "beats_count": len(beats),
                }
            )
    log(f"[OK] wrote sweep summary -> {out_path}", True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
