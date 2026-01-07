"""Smoke helpers."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ma_helper.core.config import RuntimeConfig


def _get_smoke_paths(runtime: RuntimeConfig = None):
    """Get smoke script paths, with backward compatibility."""
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root

    smoke_script = root / "infra" / "scripts" / "smoke_full_chain.sh"
    out_root = root / "data" / "features_output" / "smoke"
    return smoke_script, out_root


def _latest_run_dir(runtime: RuntimeConfig = None) -> Path | None:
    _, out_root = _get_smoke_paths(runtime)
    if not out_root.exists():
        return None
    candidates = sorted(out_root.glob("*/*"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def run_smoke(audio_file: Path, python_bin: Path, runtime: RuntimeConfig = None) -> int:
    """
    Run the canonical full-chain smoke with a supplied audio file.
    SAFE by default; writes only under data/features_output/smoke.
    """
    smoke_script, out_root = _get_smoke_paths(runtime)

    # Backward compatibility for root
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root

    if not smoke_script.exists():
        print(f"[ma] smoke script missing: {smoke_script}")
        return 1
    if not audio_file.exists():
        print(f"[ma] audio not found: {audio_file}")
        return 1
    env = os.environ.copy()
    env["PY"] = str(python_bin)
    print(f"[ma] OUT_ROOT={out_root}", flush=True)
    print(f"[ma] smoke: {audio_file} via {smoke_script.name} (PY={python_bin})")
    rc = subprocess.call(
        ["zsh", str(smoke_script), str(audio_file)],
        cwd=root,
        env=env,
    )
    latest = _latest_run_dir(runtime)
    if latest:
        print(f"[ma] OUT_DIR={latest}", flush=True)
    return rc
