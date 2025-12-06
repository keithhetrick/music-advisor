"""
CLI/import smoke checks for monorepo readiness.

These tests ensure key entrypoints still import and expose --help without
path hacks. They are light and fast: no external side-effects.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "bin" / "python"
PY = PY if PY.exists() else Path("python3")


def run_cli(args: list[str]) -> int:
    return subprocess.run([str(PY), *args], cwd=ROOT, capture_output=True).returncode


def test_pipeline_driver_help():
    assert run_cli(["tools/pipeline_driver.py", "--help"]) == 0


def test_audio_metadata_probe_help():
    assert run_cli(["-m", "tools.audio_metadata_probe", "--help"]) == 0
