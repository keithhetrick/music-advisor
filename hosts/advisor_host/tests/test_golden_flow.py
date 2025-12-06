import json
import os
import subprocess
import sys
from pathlib import Path


def test_golden_flow_analyze_groove_more_loudness(tmp_path):
    root = Path(__file__).resolve().parents[3]
    client = root / "hosts/advisor_host/tests/fixtures/sample_client.json"
    session_file = tmp_path / "sess.json"

    # Analyze (save session)
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
    subprocess.check_output(cmd1, cwd=root, env=env)

    # Groove query
    cmd2 = [
        sys.executable,
        "-m",
        "advisor_host.cli.session_cli",
        "--message",
        "groove?",
        "--load",
        str(session_file),
        "--save",
        str(session_file),
    ]
    out2 = subprocess.check_output(cmd2, cwd=root, env=env)
    data2 = json.loads(out2.decode())
    assert data2["session_id"]

    # More (paging)
    cmd3 = [
        sys.executable,
        "-m",
        "advisor_host.cli.session_cli",
        "--message",
        "more",
        "--load",
        str(session_file),
        "--save",
        str(session_file),
    ]
    out3 = subprocess.check_output(cmd3, cwd=root, env=env)
    data3 = json.loads(out3.decode())
    assert data3["session_id"] == data2["session_id"]

    # Loudness query
    cmd4 = [
        sys.executable,
        "-m",
        "advisor_host.cli.session_cli",
        "--message",
        "loudness?",
        "--load",
        str(session_file),
    ]
    out4 = subprocess.check_output(cmd4, cwd=root, env=env)
    data4 = json.loads(out4.decode())
    assert data4["session_id"] == data2["session_id"]
