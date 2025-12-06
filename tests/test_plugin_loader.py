from ma_audio_engine.adapters import plugin_loader


def test_list_plugins_empty_for_missing_kind(tmp_path, monkeypatch):
    monkeypatch.setattr(plugin_loader, "_PLUGINS_ROOT", tmp_path)
    assert plugin_loader.list_plugins("nonexistent") == {}
    assert plugin_loader.load_plugin("nonexistent", "foo") is None


def test_load_logging_plugin():
    plugins = plugin_loader.list_plugins("logging")
    assert "json_printer" in plugins
    factory = plugin_loader.load_factory("logging", "json_printer")
    logger = factory(prefix="plugin_test")
    assert callable(logger)
