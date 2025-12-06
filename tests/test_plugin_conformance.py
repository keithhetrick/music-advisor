from __future__ import annotations

import json
from pathlib import Path

import pytest

from ma_audio_engine.adapters.plugin_loader import load_factory


@pytest.mark.parametrize(
    "kind,name",
    [
        ("logging", "json_printer"),
        ("logging", "http_post"),
    ],
)
def test_logging_plugins_factory_callable(kind: str, name: str):
    factory = load_factory(kind, name)
    assert callable(factory), f"{kind}.{name} factory missing"
    logger = factory(prefix="test", defaults={"endpoint": "http://127.0.0.1:9", "max_retries": 1})
    assert callable(logger)


@pytest.mark.parametrize(
    "plugin",
    ["stub", "rich_stub"],
)
def test_sidecar_plugins_write_output(tmp_path: Path, plugin: str):
    factory = load_factory("sidecar", plugin)
    assert callable(factory)
    runner = factory()
    out = tmp_path / "sidecar.json"
    rc = runner("dummy.wav", str(out))
    assert rc == 0
    data = json.loads(out.read_text())
    assert "tempo" in data and "backend" in data


def test_cache_plugin_roundtrip():
    factory = load_factory("cache", "memory_cache")
    cache = factory()
    cache.store("hash", "fingerprint", {"foo": "bar"}, source_mtime=123.0)
    loaded = cache.load("hash", "fingerprint", source_mtime=123.0)
    assert loaded["foo"] == "bar"


def test_exporter_plugin(tmp_path: Path, capsys):
    factory = load_factory("exporter", "echo_stdout")
    assert callable(factory)
    export = factory()
    export({"hello": "world"}, tmp_path / "out.json")
    out = capsys.readouterr().out
    assert "hello" in out and "out.json" in out
