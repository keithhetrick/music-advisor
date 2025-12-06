from pathlib import Path

from ma_core.profiles import resolve_profile_config


def test_resolve_profile_config_cli_over_env(monkeypatch, tmp_path):
    env_cfg = tmp_path / "env.json"
    env_cfg.write_text('{"profile": "env_config"}', encoding="utf-8")
    monkeypatch.setenv("TEST_PROFILE_ENV", "env_profile")
    monkeypatch.setenv("TEST_CONFIG_ENV", str(env_cfg))

    cli_cfg = tmp_path / "cli.json"
    cli_cfg.write_text('{"profile": "cli_config"}', encoding="utf-8")
    logs = []

    profile, path, cfg = resolve_profile_config(
        cli_profile="cli_profile",
        cli_config=str(cli_cfg),
        env_profile_var="TEST_PROFILE_ENV",
        env_config_var="TEST_CONFIG_ENV",
        default_profile="default_profile",
        default_config_path=Path("default.json"),
        log=logs.append,
    )
    assert profile == "cli_profile"
    assert path == cli_cfg
    assert cfg["profile"] == "cli_config"
    assert logs == []


def test_resolve_profile_config_allows_profile_as_path(tmp_path):
    profile_path = tmp_path / "profile.json"
    profile_path.write_text('{"calibration_profile": "from_file", "profile": "in_file"}', encoding="utf-8")

    profile, path, cfg = resolve_profile_config(
        cli_profile=str(profile_path),
        cli_config=None,
        env_profile_var="TEST_PROFILE_ENV2",
        env_config_var="TEST_CONFIG_ENV2",
        default_profile="default_profile",
        default_config_path=Path("default.json"),
        log=lambda *_args, **_kwargs: None,
    )
    assert path == profile_path
    assert profile == "from_file"
    assert cfg["profile"] == "in_file"


def test_resolve_profile_config_uses_config_when_no_overrides(monkeypatch, tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text('{"profile": "config_profile"}', encoding="utf-8")
    monkeypatch.delenv("TEST_PROFILE_ENV3", raising=False)
    monkeypatch.delenv("TEST_CONFIG_ENV3", raising=False)
    logs = []

    profile, path, cfg = resolve_profile_config(
        cli_profile=None,
        cli_config=None,
        env_profile_var="TEST_PROFILE_ENV3",
        env_config_var="TEST_CONFIG_ENV3",
        default_profile="default_profile",
        default_config_path=cfg_path,
        log=logs.append,
    )
    assert profile == "config_profile"
    assert path == cfg_path
    assert cfg["profile"] == "config_profile"
