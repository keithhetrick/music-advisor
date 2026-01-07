"""Tests for logger_factory.py"""
from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stderr
from unittest import mock

import pytest

from shared.ma_utils.logger_factory import get_configured_logger


class TestGetConfiguredLogger:
    """Test suite for get_configured_logger factory function."""

    def test_default_behavior_plain_logger(self):
        """Test that default behavior creates a plain logger reading from env."""
        with mock.patch.dict(os.environ, {"LOG_JSON": "0", "LOG_REDACT": "0"}, clear=False):
            log = get_configured_logger("test_tool")

            # Capture stderr output
            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("test message")

            output = stderr_capture.getvalue()
            assert "test_tool" in output
            assert "test message" in output
            # Should not be JSON
            with pytest.raises(json.JSONDecodeError):
                json.loads(output)

    def test_structured_logger_from_env(self):
        """Test structured logger created when LOG_JSON=1 in environment."""
        with mock.patch.dict(os.environ, {"LOG_JSON": "1"}, clear=False):
            log = get_configured_logger("test_tool")

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("test_event", {"status": "ok"})

            output = stderr_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed["prefix"] == "test_tool"
            assert parsed["event"] == "test_event"
            assert parsed["status"] == "ok"

    def test_structured_override(self):
        """Test explicit structured=True overrides environment."""
        with mock.patch.dict(os.environ, {"LOG_JSON": "0"}, clear=False):
            log = get_configured_logger("test_tool", structured=True)

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("test_event", {})

            output = stderr_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed["event"] == "test_event"

    def test_redaction_from_env(self):
        """Test redaction when LOG_REDACT=1 and LOG_REDACT_VALUES set."""
        with mock.patch.dict(
            os.environ,
            {"LOG_REDACT": "1", "LOG_REDACT_VALUES": "secret123,password456", "LOG_JSON": "0"},
            clear=False
        ):
            log = get_configured_logger("test_tool")

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("My secret123 and password456 here")

            output = stderr_capture.getvalue()
            assert "secret123" not in output
            assert "password456" not in output
            assert "***" in output

    def test_redaction_explicit_override(self):
        """Test explicit redact=True with custom redact_values."""
        with mock.patch.dict(os.environ, {"LOG_REDACT": "0", "LOG_JSON": "0"}, clear=False):
            log = get_configured_logger(
                "test_tool",
                redact=True,
                redact_values=["custom_secret"]
            )

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("This is a custom_secret value")

            output = stderr_capture.getvalue()
            assert "custom_secret" not in output
            assert "***" in output

    def test_redaction_disabled_explicitly(self):
        """Test that redact=False disables redaction even if env says otherwise."""
        with mock.patch.dict(
            os.environ,
            {"LOG_REDACT": "1", "LOG_REDACT_VALUES": "secret", "LOG_JSON": "0"},
            clear=False
        ):
            log = get_configured_logger("test_tool", redact=False)

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("This is a secret value")

            output = stderr_capture.getvalue()
            # With redact=False, secret should NOT be redacted
            assert "secret" in output

    def test_structured_with_defaults(self):
        """Test structured logger with default fields."""
        with mock.patch.dict(os.environ, {"LOG_JSON": "0"}, clear=False):
            log = get_configured_logger(
                "test_tool",
                structured=True,
                defaults={"version": "1.0", "environment": "test"}
            )

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("my_event", {"custom_field": "value"})

            output = stderr_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed["version"] == "1.0"
            assert parsed["environment"] == "test"
            assert parsed["custom_field"] == "value"
            assert parsed["event"] == "my_event"

    def test_empty_redact_values_from_env(self):
        """Test handling of empty LOG_REDACT_VALUES."""
        with mock.patch.dict(
            os.environ,
            {"LOG_REDACT": "1", "LOG_REDACT_VALUES": "", "LOG_JSON": "0"},
            clear=False
        ):
            log = get_configured_logger("test_tool")

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("No secrets to redact")

            output = stderr_capture.getvalue()
            assert "No secrets to redact" in output

    def test_comma_separated_redact_values(self):
        """Test parsing comma-separated redact values."""
        with mock.patch.dict(
            os.environ,
            {"LOG_REDACT": "1", "LOG_REDACT_VALUES": "val1,val2,val3", "LOG_JSON": "0"},
            clear=False
        ):
            log = get_configured_logger("test_tool")

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("Contains val1 and val2 and val3")

            output = stderr_capture.getvalue()
            assert "val1" not in output
            assert "val2" not in output
            assert "val3" not in output
            # Should have three redacted instances
            assert output.count("***") == 3

    def test_all_env_vars_unset(self):
        """Test behavior when no environment variables are set."""
        # Clear relevant env vars
        env_without_log_vars = {k: v for k, v in os.environ.items()
                                 if not k.startswith("LOG_")}
        with mock.patch.dict(os.environ, env_without_log_vars, clear=True):
            log = get_configured_logger("test_tool")

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log("test message")

            output = stderr_capture.getvalue()
            # Should default to plain logger, no JSON
            assert "test message" in output
            with pytest.raises(json.JSONDecodeError):
                json.loads(output)

    def test_home_path_redaction(self):
        """Test that home paths are automatically shortened to ~."""
        from pathlib import Path
        home = str(Path.home())

        with mock.patch.dict(os.environ, {"LOG_JSON": "0", "LOG_REDACT": "0"}, clear=False):
            log = get_configured_logger("test_tool")

            stderr_capture = io.StringIO()
            with redirect_stderr(stderr_capture):
                log(f"Path is {home}/myfile.txt")

            output = stderr_capture.getvalue()
            assert home not in output
            assert "~/myfile.txt" in output
