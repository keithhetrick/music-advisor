import json
from pathlib import Path

from advisor_host.diagnostics.diagnostics import _hash_user, gather_diagnostics


def test_gather_diagnostics_redacts(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    sample = {
        "timestamp": "2025-01-01T00:00:00Z",
        "event": "handle_message",
        "data": {"intent": "plan", "payload": "secret", "norms": "nope", "reply_len": 10},
    }
    log.write_text(json.dumps(sample) + "\n", encoding="utf-8")
    bundle = gather_diagnostics(log, user_id="user123", app_version="1.0.0")
    assert "logs" in bundle
    assert bundle["user"] == _hash_user("user123")
    entry = bundle["logs"][0]
    assert "payload" not in entry.get("data", {})
    assert "norms" not in entry.get("data", {})
