import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("transcript_file", ["golden_chat.json", "golden_chat_norms.json"])
def test_golden_transcript_cli(transcript_file):
    root = Path(__file__).resolve().parents[3]
    transcript_path = root / "hosts/advisor_host/tests" / transcript_file
    steps = json.loads(transcript_path.read_text())
    session_file = transcript_path.with_suffix(".sess.json")
    env = {"PYTHONPATH": os.pathsep.join([str(root / "hosts"), str(root / "vendor")])}

    # start with analyze (first step must have payload)
    first = steps[0]
    cmd = [
        sys.executable,
        "-m",
        "advisor_host.cli.session_cli",
        "--message",
        first["message"],
        "--payload",
        str(root / "hosts" / "advisor_host" / "tests" / "fixtures" / Path(first["payload"]).name),
        "--save",
        str(session_file),
    ]
    subprocess.check_output(cmd, cwd=root, env=env)

    for step in steps[1:]:
        cmd = [
            sys.executable,
            "-m",
            "advisor_host.cli.session_cli",
            "--message",
            step["message"],
            "--load",
            str(session_file),
            "--save",
            str(session_file),
        ]
        out = subprocess.check_output(cmd, cwd=root, env=env)
        resp = json.loads(out.decode())
        for key in step.get("expect_keys", []):
            assert key in resp
