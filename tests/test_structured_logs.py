import json
from ma_audio_engine.adapters import service_registry


def test_structured_logger_basic(capsys):
    log = service_registry.get_structured_logger(prefix="test", defaults={"tool": "demo"})
    log("start", {"foo": "bar"})
    out = capsys.readouterr().err.strip()
    payload = json.loads(out)
    assert payload["prefix"] == "test"
    assert payload["event"] == "start"
    assert payload["tool"] == "demo"
    assert payload["foo"] == "bar"
