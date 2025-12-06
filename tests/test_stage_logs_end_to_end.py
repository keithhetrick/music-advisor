import json
import os
import subprocess
import sys
from pathlib import Path


def _run(cmd, env):
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def test_ma_audio_features_stage_logs_with_stub_sidecar(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    audio = repo / "tone.wav"
    out = tmp_path / "out.features.json"
    env = os.environ.copy()
    env.update(
        {
            "LOG_JSON": "1",
            "MA_SIDECAR_PLUGIN": "stub",
            "PYTHONPATH": f"{repo}:{repo/'src'}",
        }
    )
    cmd = [
        sys.executable,
        str(repo / "tools" / "ma_audio_features.py"),
        "--audio",
        str(audio),
        "--out",
        str(out),
        "--tempo-backend",
        "sidecar",
        "--require-sidecar",
    ]
    rc, _stdout, stderr = _run(cmd, env)
    assert rc == 0
    stage_end = None
    for line in stderr.splitlines():
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if payload.get("event") == "stage_end" and payload.get("stage") == "analyze_pipeline":
            stage_end = payload
            break
    assert stage_end, f"stage_end log not found in stderr:\n{stderr}"
    assert "sidecar_lint_warnings" in stage_end
    assert stage_end.get("status") == "ok"


def test_log_summary_strict_passes_on_fixtures():
    repo = Path(__file__).resolve().parents[1]
    out_dir = repo / "tests" / "fixtures"
    env = os.environ.copy()
    env.update({"LOG_JSON": "0", "PYTHONPATH": f"{repo}:{repo/'src'}"})
    cmd = [sys.executable, str(repo / "tools" / "log_summary.py"), "--out-dir", str(out_dir), "--strict"]
    rc, _stdout, _stderr = _run(cmd, env)
    assert rc == 0
