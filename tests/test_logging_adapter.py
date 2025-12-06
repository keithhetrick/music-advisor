from ma_audio_engine.adapters import service_registry
import json


def test_structured_logger_outputs_json(capsys):
    log = service_registry.get_structured_logger(prefix="test", defaults={"stage": "unit"})
    log("event_name", {"foo": "bar"})
    out = capsys.readouterr().err.strip()
    payload = json.loads(out)
    assert payload["prefix"] == "test"
    assert payload["event"] == "event_name"
    assert payload["stage"] == "unit"
    assert payload["foo"] == "bar"
