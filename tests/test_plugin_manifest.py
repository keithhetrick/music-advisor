import json
from pathlib import Path

from ma_audio_engine.adapters.plugin_loader import load_factory


def test_manifest_factories_callable():
    manifest = json.loads((Path("plugins/manifest.json")).read_text())
    for kind, entries in manifest.items():
        for name, module_path in entries.items():
            factory = load_factory(kind, name)
            assert callable(factory), f"{kind}.{name} factory not callable ({module_path})"
