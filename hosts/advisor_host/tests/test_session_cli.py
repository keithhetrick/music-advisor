import json
import os
import subprocess
import sys
from pathlib import Path


def test_session_cli_save_load(tmp_path):
    root = Path(__file__).resolve().parents[3]
    client = root / "hosts/advisor_host/tests/fixtures/sample_client.json"
    session_file = tmp_path / "sess.json"
    # First message with payload, save session
    cmd1 = [
        sys.executable,
        "-m",
        "advisor_host.cli.session_cli",
        "--message",
        "analyze",
        "--payload",
        str(client),
        "--save",
        str(session_file),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "hosts"), str(root / "vendor")])
    out1 = subprocess.check_output(cmd1, cwd=root, env=env)
    data1 = json.loads(out1.decode())
    assert data1["session_id"]
    assert session_file.exists()
    # Follow-up using loaded session
    cmd2 = [
        sys.executable,
        "-m",
        "advisor_host.cli.session_cli",
        "--message",
        "more",
        "--load",
        str(session_file),
    ]
    out2 = subprocess.check_output(cmd2, cwd=root, env=env)
    data2 = json.loads(out2.decode())
    assert data2["session_id"] == data1["session_id"]
