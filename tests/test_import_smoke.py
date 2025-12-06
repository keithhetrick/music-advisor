"""
Lightweight import smoke test to guard modularity/monorepo-readiness.

We only assert that core modules import without sys.path hacks or runtime
side effects. This catches regressions when files move in a monorepo reorg.
"""
from importlib import import_module

MODULES = [
    "ma_config.paths",
    "ma_config.pipeline",
    "ma_audio_engine.extract_cli",
    "ma_audio_engine.pipe_cli",
    "ma_audio_engine.always_present",
    "tools.pipeline_driver",
    "tools.audio_metadata_probe",
    "tools.append_metadata_to_client_rich",
    "tools.echo_services",
    "tools.hci.ma_add_echo_to_client_rich_v1",
    "tools.hci_echo_probe_from_spine_v1",
]


def test_imports_smoke():
    for mod in MODULES:
        import_module(mod)
