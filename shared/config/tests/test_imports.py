import importlib


def test_import_shared_config():
    importlib.import_module("shared.config")
