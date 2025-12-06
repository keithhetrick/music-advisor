"""
Service registry adapter.

Purpose:
- Provide a single import point for core services (QA policy, logging, cache, export) so callers stay decoupled from concrete implementations.
- Support plugin overrides via env without touching pipeline callers.

Config hooks:
- Exporter plugin: env MA_EXPORTER_PLUGIN (plugin factory under plugins/exporter/<name>.py)
- Logging plugin: env MA_LOGGING_PLUGIN (structured logger factory under plugins/logging/<name>.py)
- Cache/logging/QA policy defaults come from their respective adapters and config files.

Usage:
- `get_exporter()` returns a callable writing JSON by default (or plugin override).
- `get_logger()` / `get_structured_logger()` return logger functions (plugin-aware).
- `get_qa_policy(name)` proxies to qa_policy_adapter.
- `get_cache(cache_dir, backend)` returns a CacheAdapter (noop if no cache dir and backend not disk).
- `scrub_payload_for_sandbox(payload)` applies logging sandbox redaction defaults.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Callable

import os
import os
from ma_audio_engine.adapters.qa_policy_adapter import load_qa_policy
from ma_audio_engine.adapters.logging_adapter import make_logger, make_structured_logger, sandbox_options, sandbox_scrub_payload
from ma_audio_engine.adapters.cache_adapter import CacheAdapter
from ma_audio_engine.adapters_src import plugin_loader

# Optional export hook: default is simple JSON writer
def get_exporter() -> Callable[[dict, Path], None]:
    plugin_name = os.getenv("MA_EXPORTER_PLUGIN")
    if plugin_name:
        factory = plugin_loader.load_factory("exporter", plugin_name)
        if factory:
            try:
                return factory()
            except Exception:
                pass
    def _export(payload: dict, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    return _export


def get_logger(prefix: str = "", redact: Optional[bool] = None, secrets: Optional[list] = None, plugin: Optional[str] = None) -> Callable[[str], None]:
    base = make_logger(prefix=prefix, redact=bool(redact) if redact is not None else False, secrets=secrets)
    plugin_name = plugin or os.getenv("MA_LOGGING_PLUGIN")
    if plugin_name:
        factory = plugin_loader.load_factory("logging", plugin_name)
        if factory:
            try:
                plugin_logger = factory(prefix=prefix, defaults={"plugin": plugin_name})
                def _log(msg: str) -> None:
                    base(msg)
                    try:
                        plugin_logger("log", {"message": msg})
                    except Exception:
                        pass
                return _log
            except Exception:
                pass
    return base


def get_structured_logger(prefix: str = "", defaults: Optional[dict] = None, plugin: Optional[str] = None) -> Callable[[str, dict], None]:
    base = make_structured_logger(prefix=prefix, defaults=defaults)
    plugin_name = plugin or os.getenv("MA_LOGGING_PLUGIN")
    if plugin_name:
        factory = plugin_loader.load_factory("logging", plugin_name)
        if factory:
            try:
                plugin_logger = factory(prefix=prefix, defaults=defaults or {"plugin": plugin_name})
                def _log(event: str, fields: Optional[dict] = None) -> None:
                    base(event, fields)
                    try:
                        plugin_logger(event, fields or {})
                    except Exception:
                        pass
                return _log
            except Exception:
                pass
    return base


def get_qa_policy(name: str):
    return load_qa_policy(name)


def get_cache(cache_dir: Optional[str], backend: Optional[str] = None) -> CacheAdapter:
    return CacheAdapter(cache_dir, backend=backend) if cache_dir else CacheAdapter(backend=backend)


def get_logging_sandbox_defaults() -> dict[str, Any]:
    return sandbox_options()


def scrub_payload_for_sandbox(payload: dict, sandbox: Optional[dict] = None) -> dict:
    return sandbox_scrub_payload(payload, sandbox)
