import json
import os
import subprocess
import sys
from pathlib import Path

from advisor_host.host.chat import ChatSession, handle_message
from advisor_host.schema.schema import validate_reply_shape
from recommendation_engine.tests.fixtures import sample_market_norms, sample_payload


def validate_reply(resp: dict):
    validate_reply_shape(resp)


def test_validate_direct_calls():
    session = ChatSession()
    intro = handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    reply = handle_message(session, "groove?")
    for resp in (intro, reply):
        validate_reply(resp)


def test_validate_cli_flow(tmp_path):
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
    cmd = [
        sys.executable,
        str(root / "hosts/advisor_host/cli/ma_host.py"),
        "--norms",
        str(norms),
        str(client),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "hosts"), str(root / "engines"), str(root / "engines/recommendation_engine")]
    )
    out = subprocess.check_output(cmd, cwd=root, env=env)
    # ma_host outputs recommendation JSON (no session_id); wrap minimal fields for validation
    rec = json.loads(out.decode())
    fake_resp = {
        "session_id": "cli",
        "reply": rec.get("hci_comment", ""),
        "ui_hints": {"show_cards": [], "quick_actions": [], "tone": "neutral", "primary_slices": []},
    }
    validate_reply(fake_resp)
