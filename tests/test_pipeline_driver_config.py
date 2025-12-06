import json
from pathlib import Path

from tools import pipeline_driver


# This test ensures the JSON config override surface stays stable:
# only known keys are applied, with defaults coming from ma_config.pipeline.


def test_load_pipeline_config_overrides(tmp_path: Path):
    cfg_file = tmp_path / "cfg.json"
    cfg_file.write_text(
        json.dumps(
            {
                "hci_builder_profile": "custom_hci",
                "neighbors_profile": "custom_neighbors",
                "sidecar_timeout_seconds": 999,
            }
        ),
        encoding="utf-8",
    )
    cfg = pipeline_driver.load_pipeline_config(cfg_file)
    assert cfg["hci_builder_profile"] == "custom_hci"
    assert cfg["neighbors_profile"] == "custom_neighbors"
    assert cfg["sidecar_timeout_seconds"] == 999
