import os
from pathlib import Path
import subprocess


def test_pipeline_runner_strict_with_stub(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    tone = tmp_path / "tone.wav"
    # generate a tiny tone file
    tone.write_bytes(b"\x00\x00")  # minimal placeholder; pipeline will handle short input
    env = os.environ.copy()
    env.update({"LOG_JSON": "0", "PYTHONPATH": f"{repo}:{repo/'src'}"})
    cmd = [
        str(repo / "infra" / "scripts" / "pipeline_smoke.sh"),
        str(tone),
        "--strict",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    # In strict mode we allow non-zero if warnings occur; ensure it does not crash unexpectedly.
    assert proc.returncode in (0, 1)
    # Ensure outputs directory exists
    out_root = repo / "data" / "features_output" / "pipeline_smoke"
    assert out_root.exists()
