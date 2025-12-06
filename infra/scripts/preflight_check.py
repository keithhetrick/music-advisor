#!/usr/bin/env python3
"""
Preflight checks for MusicAdvisor Audio Tools.
Verifies required files, env, and pinned dependencies.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
from pathlib import Path

from ma_config.paths import get_historical_echo_db_path
from ma_config.audio import DEFAULT_HCI_CALIBRATION_PATH, DEFAULT_MARKET_NORMS_PATH

REPO = Path(__file__).resolve().parents[1]
ENV_JSON = os.environ.get("LOG_JSON", "0") == "1"


def _emit(status: str, label: str, detail: str = "") -> None:
    payload = {"status": status, "label": label, "detail": detail}
    if ENV_JSON:
        print(json.dumps(payload))
    else:
        suffix = f": {detail}" if detail else ""
        print(f"[{status}] {label}{suffix}")


def check_file(label: str, path: Path, required: bool = True) -> bool:
    if path.exists():
        _emit("OK", label, str(path))
        return True
    if required:
        _emit("ERR", label, f"missing -> {path}")
        return False
    _emit("WARN", label, f"missing (optional) -> {path}")
    return True


def check_module(label: str, want_version: str | None, required: bool = True) -> bool:
    try:
        mod = importlib.import_module(label)
        have = getattr(mod, "__version__", "unknown")
    except Exception:
        if required:
            _emit("ERR", f"python:{label}", "missing")
            return False
        _emit("WARN", f"python:{label}", "missing (optional)")
        return True
    if want_version and have != want_version:
        _emit("ERR", f"python:{label}", f"{have} (want {want_version})")
        return False
    _emit("OK", f"python:{label}", have if want_version else "present")
    return True


def check_cmd(label: str, cmd: str, required: bool = True) -> bool:
    if shutil.which(cmd):
        _emit("OK", f"cmd:{label}", shutil.which(cmd) or cmd)
        return True
    if required:
        _emit("ERR", f"cmd:{label}", "not found on PATH")
        return False
    _emit("WARN", f"cmd:{label}", "not found (optional)")
    return True


def main() -> int:
    ok = True

    # Files / datasets
    checks = [
        ("CORE_PATH (optional)", REPO / "data" / "spine" / "spine_core_tracks_v1.csv", False),
        ("Historical Echo DB (optional)", get_historical_echo_db_path(REPO / "data"), False),
        ("Calibration JSON", DEFAULT_HCI_CALIBRATION_PATH, True),
        ("Market Norms", DEFAULT_MARKET_NORMS_PATH, True),
        ("Neighbors schema", REPO / "schemas" / "neighbors.schema.json", True),
        ("Pack schema", REPO / "schemas" / "pack.schema.json", True),
        ("Run summary schema", REPO / "schemas" / "run_summary.schema.json", True),
    ]
    for label, path, required in checks:
        ok &= check_file(label, path, required)

    # Python dependencies (pinned)
    for mod, ver, required in [
        ("numpy", "1.26.4", True),
        ("scipy", "1.11.4", True),
        ("librosa", "0.10.1", True),
        ("essentia", None, False),
        ("madmom", None, False),  # optional
    ]:
        ok &= check_module(mod, ver, required)

    # CLI/tooling
    ok &= check_cmd("python", "python3", True)
    ok &= check_cmd("ffmpeg", "ffmpeg", True)
    ok &= check_cmd("ffprobe", "ffprobe", False)

    sidecar_py = REPO / "tools" / "tempo_sidecar_runner.py"
    ok &= check_file("Tempo sidecar runner", sidecar_py, True)

    venv_bin = REPO / ".venv" / "bin"
    for name in ("ma-audio-features", "ma-add-echo-hci", "ma-add-echo-client", "tempo-sidecar-runner"):
        path = venv_bin / name
        ok &= check_file(f"entrypoint:{name}", path, required=False)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
