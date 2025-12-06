# Central adapter exports for easy, consistent imports across tools.
# Prefer importing from adapters rather than individual modules when practical.

from ma_audio_engine.adapters.logging_adapter import (  # noqa: F401
    LOG_REDACT,
    LOG_REDACT_VALUES,
    make_logger,
    log_stage_start,
    log_stage_end,
)
from ma_audio_engine.adapters.settings_adapter import load_log_settings, load_runtime_settings  # noqa: F401
from ma_audio_engine.adapters.time_adapter import utc_now_iso  # noqa: F401
import sys
from pathlib import Path

from ma_audio_engine.adapters.qa_policy_adapter import load_qa_policy  # noqa: F401
from ma_audio_engine.adapters.cache_adapter import get_cache  # noqa: F401
from ma_audio_engine.adapters.backend_registry_adapter import (  # noqa: F401
    list_supported_backends,
    is_backend_enabled,
    get_default_sidecar_cmd,
    get_backend_settings,
    get_sidecar_cmd_for_backend,
    validate_sidecar_cmd,
)
from ma_audio_engine.adapters.error_adapter import load_json_guarded, require_file  # noqa: F401
from ma_audio_engine.adapters.preflight_adapter import validate_root_dir  # noqa: F401
from ma_audio_engine.adapters.neighbor_adapter import write_neighbors_file  # noqa: F401
from ma_audio_engine.adapters.config_adapter import resolve_config_value, build_config_components  # noqa: F401
from ma_audio_engine.adapters.confidence_adapter import (  # noqa: F401
    confidence_label,
    normalize_tempo_confidence,
    TEMPO_CONF_DEFAULTS,
)
from ma_audio_engine.adapters.hash_adapter import get_hash_params, hash_file  # noqa: F401
from ma_audio_engine.adapters.audio_loader_adapter import load_audio_mono  # noqa: F401
from ma_audio_engine.adapters.cli_adapter import (  # noqa: F401
    add_log_sandbox_arg,
    apply_log_sandbox_env,
    add_qa_policy_arg,
    add_log_format_arg,
    apply_log_format_env,
    add_preflight_arg,
    run_preflight_if_requested,
)

__all__ = [
    "LOG_REDACT",
    "LOG_REDACT_VALUES",
    "make_logger",
    "log_stage_start",
    "log_stage_end",
    "load_log_settings",
    "load_runtime_settings",
    "utc_now_iso",
    "load_qa_policy",
    "get_cache",
    "list_supported_backends",
    "is_backend_enabled",
    "get_default_sidecar_cmd",
    "get_backend_settings",
    "get_sidecar_cmd_for_backend",
    "validate_sidecar_cmd",
    "load_json_guarded",
    "require_file",
    "validate_root_dir",
    "write_neighbors_file",
    "add_log_sandbox_arg",
    "apply_log_sandbox_env",
    "add_qa_policy_arg",
    "add_log_format_arg",
    "apply_log_format_env",
    "add_preflight_arg",
    "run_preflight_if_requested",
    "resolve_config_value",
    "build_config_components",
    "confidence_label",
    "normalize_tempo_confidence",
    "TEMPO_CONF_DEFAULTS",
    "get_hash_params",
    "hash_file",
    "load_audio_mono",
]
"""
Adapters package initializer.

Purpose:
- Expose adapter modules as a package for import convenience.
- No side effects; configuration lives in individual adapter modules and config files.

Docs:
- See adapters/README.md and docs/adapters.md for adapter catalog, config/env knobs, side effects, and usage.
"""
