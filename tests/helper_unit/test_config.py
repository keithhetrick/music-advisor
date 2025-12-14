import os
from pathlib import Path

from ma_helper.core.config import HelperConfig


def test_config_defaults_tmp(tmp_path: Path, monkeypatch):
    # no config file; should default to ma_orchestrator and registry path under root
    monkeypatch.chdir(tmp_path)
    cfg = HelperConfig.load(tmp_path)
    assert cfg.adapter == "ma_orchestrator"
    assert cfg.registry_path == tmp_path / "project_map.json"
    assert cfg.task_aliases == {}


def test_config_env_overrides(tmp_path: Path, monkeypatch):
    cfg_path = tmp_path / "ma_helper.toml"
    cfg_path.write_text(
        """
adapter = "ma_orchestrator"
registry_path = "custom_map.json"
[tasks]
foo = "echo hi"
"""
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MA_HELPER_ADAPTER", "ma_orchestrator")
    monkeypatch.setenv("MA_HELPER_REGISTRY", str(tmp_path / "env_map.json"))
    cfg = HelperConfig.load(tmp_path)
    assert cfg.adapter == "ma_orchestrator"
    assert cfg.registry_path == tmp_path / "env_map.json"
    assert cfg.task_aliases.get("foo") == "echo hi"


def test_no_write_disables_paths(tmp_path: Path, monkeypatch):
    cfg_path = tmp_path / "ma_helper.toml"
    cfg_path.write_text(
        """
state_dir = "state_dir"
log_file = "log.log"
cache_dir = "cache_dir"
"""
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MA_HELPER_NO_WRITE", "1")
    cfg = HelperConfig.load(tmp_path)
    assert cfg.state_dir is None
    assert cfg.log_file is None
    assert cfg.cache_dir is None
