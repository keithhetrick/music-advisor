"""Smoke helpers."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ma_helper.core.env import ROOT

SMOKE_SCRIPT = ROOT / "infra" / "scripts" / "smoke_full_chain.sh"
OUT_ROOT = ROOT / "data" / "features_output" / "smoke"


def _latest_run_dir() -> Path | None:
    if not OUT_ROOT.exists():
        return None
    candidates = sorted(OUT_ROOT.glob("*/*"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def run_smoke(audio_file: Path, python_bin: Path) -> int:
    """
    Run the canonical full-chain smoke with a supplied audio file.
    SAFE by default; writes only under data/features_output/smoke.
    """
    if not SMOKE_SCRIPT.exists():
        print(f"[ma] smoke script missing: {SMOKE_SCRIPT}")
        return 1
    if not audio_file.exists():
        print(f"[ma] audio not found: {audio_file}")
        return 1
    env = os.environ.copy()
    env["PY"] = str(python_bin)
    print(f"[ma] OUT_ROOT={OUT_ROOT}", flush=True)
    print(f"[ma] smoke: {audio_file} via {SMOKE_SCRIPT.name} (PY={python_bin})")
    rc = subprocess.call(
        ["zsh", str(SMOKE_SCRIPT), str(audio_file)],
        cwd=ROOT,
        env=env,
    )
    latest = _latest_run_dir()
    if latest:
        print(f"[ma] OUT_DIR={latest}", flush=True)
    return rc
