import importlib


def test_pipeline_driver_importable():
    # Smoke test: ensure driver module imports without side effects/errors.
    # This guards against accidental top-level execution (e.g., subprocess calls on import).
    importlib.import_module("tools.pipeline_driver")
