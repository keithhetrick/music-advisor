import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_with_norms(tmp_path):
    root = Path(__file__).resolve().parents[3]
    client = root / "hosts/advisor_host/tests/fixtures/sample_client.json"
    norms = (
        root
        / "engines"
        / "recommendation_engine"
        / "recommendation_engine"
        / "tests"
        / "fixtures"
        / "market_norms_us_tier1_2024YE.json"
    )
    cmd = [sys.executable, str(root / "hosts/advisor_host/cli/ma_host.py"), "--norms", str(norms), str(client)]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "hosts"), str(root / "engines"), str(root / "engines/recommendation_engine")]
    )
    out = subprocess.check_output(cmd, cwd=root, env=env)
    data = json.loads(out.decode())
    assert "market_norms_used" in data
    assert data["market_norms_used"]["version"] == "2024-YE"


def test_cli_without_norms_sets_none(tmp_path):
    root = Path(__file__).resolve().parents[3]
    client = root / "hosts/advisor_host/tests/fixtures/sample_client.json"
    cmd = [sys.executable, str(root / "hosts/advisor_host/cli/ma_host.py"), str(client)]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "hosts"), str(root / "engines"), str(root / "engines/recommendation_engine")]
    )
    out = subprocess.check_output(cmd, cwd=root, env=env)
    data = json.loads(out.decode())
    assert "market_norms_used" in data
    assert data["market_norms_used"] is None
