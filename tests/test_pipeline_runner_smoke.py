from pathlib import Path
import os
import subprocess


def test_pipeline_runner_invokes_with_missing_audio(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    missing_audio = tmp_path / "missing.wav"
    env = os.environ.copy()
    env.update({"PYTHONPATH": f"{repo}:{repo/'src'}"})
    proc = subprocess.run(
        [str(repo / "tools" / "pipeline_runner.py"), "--audio", str(missing_audio), "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode != 0
