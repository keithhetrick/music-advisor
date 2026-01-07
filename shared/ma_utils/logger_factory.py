"""
Centralized logger factory to eliminate redundant LOG_* environment variable parsing.

This factory consolidates the repeated pattern found across tools/ where each script
manually parses LOG_JSON, LOG_REDACT, and LOG_REDACT_VALUES from environment variables.

Usage:
    from shared.ma_utils.logger_factory import get_configured_logger

    # Use defaults from environment
    log = get_configured_logger("my_tool")

    # Override specific settings
    log = get_configured_logger("my_tool", structured=True, redact=False)

Environment Variables:
    - LOG_JSON: Enable structured JSON logging (default: "0")
    - LOG_REDACT: Enable secret redaction (default: "0")
    - LOG_REDACT_VALUES: Comma-separated list of values to redact (default: "")

Notes:
    - Side effects: writes to stderr via underlying logger
    - All parameters support None to read from environment (default behavior)
    - Explicit parameter values override environment variables
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from ma_audio_engine.adapters.logging_adapter import make_logger, make_structured_logger

__all__ = [
    "get_configured_logger",
]


def get_configured_logger(
    name: str,
    structured: bool | None = None,
    redact: bool | None = None,
    redact_values: list[str] | None = None,
    defaults: dict | None = None,
) -> Callable:
    """
    Create a logger with configuration from environment or explicit overrides.

    Args:
        name: Logger name/prefix
        structured: Enable structured JSON logging. None = read from LOG_JSON env.
        redact: Enable secret redaction. None = read from LOG_REDACT env.
        redact_values: List of secrets to redact. None = read from LOG_REDACT_VALUES env.
        defaults: Additional default fields for structured logs (ignored for plain logs).

    Returns:
        Logger function. If structured=True, returns Callable[[str, dict], None].
        Otherwise returns Callable[[str], None].

    Examples:
        >>> # Use environment defaults
        >>> log = get_configured_logger("mytool")
        >>> log("Starting process")

        >>> # Force structured logging
        >>> log = get_configured_logger("mytool", structured=True, defaults={"version": "1.0"})
        >>> log("process_started", {"status": "ok"})

        >>> # Disable redaction explicitly
        >>> log = get_configured_logger("mytool", redact=False)
        >>> log("Debug info with secrets")
    """
    # Resolve structured logging mode
    if structured is None:
        structured = os.getenv("LOG_JSON", "0") == "1"

    # Resolve redaction settings
    if redact is None:
        redact = os.getenv("LOG_REDACT", "0") == "1"

    if redact_values is None:
        redact_values = [
            v for v in os.getenv("LOG_REDACT_VALUES", "").split(",") if v
        ]

    # Create appropriate logger based on mode
    if structured:
        return make_structured_logger(prefix=name, defaults=defaults)
    else:
        return make_logger(prefix=name, redact=redact, secrets=redact_values)
