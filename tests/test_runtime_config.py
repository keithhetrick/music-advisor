"""Tests for RuntimeConfig immutable dataclass."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ma_helper.core.config import HelperConfig, RuntimeConfig


@pytest.fixture
def temp_root(tmp_path):
    """Create a temporary root directory."""
    return tmp_path / "test_repo"


@pytest.fixture
def basic_helper_config(temp_root):
    """Create a basic HelperConfig for testing."""
    temp_root.mkdir(parents=True, exist_ok=True)
    return HelperConfig(
        root=temp_root,
        registry_path=temp_root / "project_map.json",
        task_aliases={},
        state_dir=None,
        log_file=None,
        telemetry_file=None,
        adapter="ma_orchestrator",
        cache_dir=None,
    )


class TestRuntimeConfigDefaults:
    """Test RuntimeConfig creation with default values."""

    def test_from_helper_config_defaults(self, basic_helper_config, temp_root):
        """Test RuntimeConfig with all defaults (no overrides)."""
        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            # Core paths
            assert runtime.root == temp_root
            assert runtime.state_home == Path.home() / ".ma_helper"

            # Cache paths
            assert runtime.cache_dir == temp_root / ".ma_cache"
            assert runtime.cache_file == temp_root / ".ma_cache" / "cache.json"
            assert runtime.last_results_file == temp_root / ".ma_cache" / "last_results.json"
            assert runtime.artifact_dir == temp_root / ".ma_cache" / "artifacts"

            # Log paths
            assert runtime.log_dir == Path.home() / ".ma_helper" / "logs"
            assert runtime.log_file == Path.home() / ".ma_helper" / "logs" / "ma.log"
            assert runtime.telemetry_file == Path.home() / ".ma_helper" / "logs" / "ma.log"

            # User state
            assert runtime.favorites_path == Path.home() / ".ma_helper" / "config.json"

            # Flags
            assert runtime.cache_enabled is True

    def test_from_helper_config_with_custom_cache_dir(self, basic_helper_config, temp_root):
        """Test RuntimeConfig with custom cache_dir from HelperConfig."""
        custom_cache = temp_root / "custom_cache"
        basic_helper_config.cache_dir = custom_cache

        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.cache_dir == custom_cache
            assert runtime.cache_file == custom_cache / "cache.json"
            assert runtime.last_results_file == custom_cache / "last_results.json"
            assert runtime.artifact_dir == custom_cache / "artifacts"

    def test_from_helper_config_with_custom_state_dir(self, basic_helper_config, temp_root):
        """Test RuntimeConfig with custom state_dir from HelperConfig."""
        custom_state = temp_root / "custom_state"
        basic_helper_config.state_dir = custom_state

        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.state_home == custom_state
            assert runtime.log_dir == custom_state / "logs"
            assert runtime.favorites_path == custom_state / "config.json"

    def test_from_helper_config_with_custom_log_file(self, basic_helper_config, temp_root):
        """Test RuntimeConfig with custom log_file from HelperConfig."""
        custom_log = temp_root / "logs" / "custom.log"
        basic_helper_config.log_file = custom_log

        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.log_file == custom_log
            # Telemetry defaults to log_file
            assert runtime.telemetry_file == custom_log

    def test_from_helper_config_with_custom_telemetry_file(self, basic_helper_config, temp_root):
        """Test RuntimeConfig with custom telemetry_file from HelperConfig."""
        custom_telemetry = temp_root / "logs" / "telemetry.log"
        basic_helper_config.telemetry_file = custom_telemetry

        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.telemetry_file == custom_telemetry


class TestRuntimeConfigEnvironmentOverrides:
    """Test RuntimeConfig with environment variable overrides."""

    def test_ma_helper_home_override(self, basic_helper_config, temp_root):
        """Test MA_HELPER_HOME environment variable override."""
        custom_home = temp_root / "custom_ma_helper"
        with patch.dict(os.environ, {"MA_HELPER_HOME": str(custom_home)}):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.state_home == custom_home
            assert runtime.log_dir == custom_home / "logs"
            assert runtime.favorites_path == custom_home / "config.json"

    def test_ma_log_file_override(self, basic_helper_config, temp_root):
        """Test MA_LOG_FILE environment variable override."""
        custom_log = temp_root / "override.log"
        with patch.dict(os.environ, {"MA_LOG_FILE": str(custom_log)}):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.log_file == custom_log

    def test_ma_telemetry_file_override(self, basic_helper_config, temp_root):
        """Test MA_TELEMETRY_FILE environment variable override."""
        custom_telemetry = temp_root / "override_telemetry.log"
        with patch.dict(os.environ, {"MA_TELEMETRY_FILE": str(custom_telemetry)}):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.telemetry_file == custom_telemetry

    def test_ma_helper_no_write_disables_caching(self, basic_helper_config):
        """Test MA_HELPER_NO_WRITE=1 disables caching and sets log files to None."""
        with patch.dict(os.environ, {"MA_HELPER_NO_WRITE": "1"}):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.cache_enabled is False
            assert runtime.log_file is None
            assert runtime.telemetry_file is None

    def test_ma_helper_no_write_with_other_value(self, basic_helper_config):
        """Test MA_HELPER_NO_WRITE with value other than '1' enables caching."""
        with patch.dict(os.environ, {"MA_HELPER_NO_WRITE": "0"}):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.cache_enabled is True
            assert runtime.log_file is not None
            assert runtime.telemetry_file is not None

    def test_environment_precedence(self, basic_helper_config, temp_root):
        """Test that environment variables have highest precedence over HelperConfig."""
        # Set custom values in HelperConfig
        basic_helper_config.log_file = temp_root / "config_log.log"
        basic_helper_config.telemetry_file = temp_root / "config_telemetry.log"

        # Override with environment variables
        env_log = temp_root / "env_log.log"
        env_telemetry = temp_root / "env_telemetry.log"
        with patch.dict(
            os.environ,
            {"MA_LOG_FILE": str(env_log), "MA_TELEMETRY_FILE": str(env_telemetry)},
        ):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            # Environment variables should win
            assert runtime.log_file == env_log
            assert runtime.telemetry_file == env_telemetry

    def test_no_write_overrides_all_logging(self, basic_helper_config, temp_root):
        """Test MA_HELPER_NO_WRITE=1 overrides even explicit log file settings."""
        # Set log files in both HelperConfig and environment
        basic_helper_config.log_file = temp_root / "config_log.log"
        env_log = temp_root / "env_log.log"

        with patch.dict(
            os.environ,
            {"MA_LOG_FILE": str(env_log), "MA_HELPER_NO_WRITE": "1"},
        ):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            # NO_WRITE should disable everything
            assert runtime.cache_enabled is False
            assert runtime.log_file is None
            assert runtime.telemetry_file is None


class TestRuntimeConfigImmutability:
    """Test that RuntimeConfig is truly immutable."""

    def test_frozen_dataclass(self, basic_helper_config):
        """Test that RuntimeConfig cannot be modified after creation."""
        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            # Attempting to modify should raise FrozenInstanceError
            with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
                runtime.root = Path("/new/path")

            with pytest.raises(Exception):
                runtime.cache_enabled = False

            with pytest.raises(Exception):
                runtime.log_file = Path("/new/log.log")

    def test_no_global_state_mutation(self, basic_helper_config):
        """Test that creating RuntimeConfig doesn't mutate any global state."""
        with patch.dict(os.environ, {}, clear=True):
            # Create first instance
            runtime1 = RuntimeConfig.from_helper_config(basic_helper_config)

            # Modify HelperConfig
            basic_helper_config.cache_dir = Path("/different/cache")

            # Create second instance
            runtime2 = RuntimeConfig.from_helper_config(basic_helper_config)

            # First instance should be unchanged
            assert runtime1.cache_dir == basic_helper_config.root / ".ma_cache"
            # Second instance should have new value
            assert runtime2.cache_dir == Path("/different/cache")


class TestRuntimeConfigPathDerivation:
    """Test that derived paths are computed correctly."""

    def test_cache_derived_paths(self, basic_helper_config, temp_root):
        """Test that cache-related paths derive from cache_dir."""
        custom_cache = temp_root / "my_cache"
        basic_helper_config.cache_dir = custom_cache

        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.cache_file == custom_cache / "cache.json"
            assert runtime.last_results_file == custom_cache / "last_results.json"
            assert runtime.artifact_dir == custom_cache / "artifacts"

    def test_state_derived_paths(self, basic_helper_config, temp_root):
        """Test that state-related paths derive from state_home."""
        custom_state = temp_root / "my_state"
        basic_helper_config.state_dir = custom_state

        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.log_dir == custom_state / "logs"
            assert runtime.favorites_path == custom_state / "config.json"

    def test_telemetry_defaults_to_log_file(self, basic_helper_config, temp_root):
        """Test that telemetry_file defaults to log_file when not specified."""
        custom_log = temp_root / "app.log"
        basic_helper_config.log_file = custom_log
        basic_helper_config.telemetry_file = None

        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.log_file == custom_log
            assert runtime.telemetry_file == custom_log


class TestRuntimeConfigEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_environment_variables(self, basic_helper_config):
        """Test that empty string environment variables are handled correctly."""
        with patch.dict(os.environ, {"MA_HELPER_HOME": "", "MA_LOG_FILE": ""}):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            # Empty MA_HELPER_HOME should be treated as not set (empty string is falsy)
            assert runtime.state_home == Path.home() / ".ma_helper"

            # Empty MA_LOG_FILE should also be treated as not set (empty string is falsy)
            # So it should fall back to the default
            assert runtime.log_file == Path.home() / ".ma_helper" / "logs" / "ma.log"

    def test_all_custom_paths(self, basic_helper_config, temp_root):
        """Test with all paths customized at once."""
        custom_state = temp_root / "state"
        custom_cache = temp_root / "cache"
        custom_log = temp_root / "log.log"
        custom_telemetry = temp_root / "telemetry.log"

        basic_helper_config.state_dir = custom_state
        basic_helper_config.cache_dir = custom_cache
        basic_helper_config.log_file = custom_log
        basic_helper_config.telemetry_file = custom_telemetry

        with patch.dict(os.environ, {}, clear=True):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.state_home == custom_state
            assert runtime.cache_dir == custom_cache
            assert runtime.log_file == custom_log
            assert runtime.telemetry_file == custom_telemetry
            assert runtime.cache_enabled is True

    def test_all_environment_overrides(self, basic_helper_config, temp_root):
        """Test with all environment variables set at once."""
        env_state = temp_root / "env_state"
        env_log = temp_root / "env_log.log"
        env_telemetry = temp_root / "env_telemetry.log"

        with patch.dict(
            os.environ,
            {
                "MA_HELPER_HOME": str(env_state),
                "MA_LOG_FILE": str(env_log),
                "MA_TELEMETRY_FILE": str(env_telemetry),
            },
        ):
            runtime = RuntimeConfig.from_helper_config(basic_helper_config)

            assert runtime.state_home == env_state
            assert runtime.log_file == env_log
            assert runtime.telemetry_file == env_telemetry
            assert runtime.cache_enabled is True
