"""
Lightweight dependency injection helpers for CLI tools.

Provides factories for logging, sidecar runner, QA policy, and cache, with
defaults wired to adapters/service_registry. CLIs can import these factories
and override via keyword args for testing.

Usage:
- `make_logger(prefix, structured=True|False, defaults={...})` to get a logger wired through service_registry.
- `make_cache(cache_dir, backend, plugin="custom_cache")` to swap cache backend via plugin/env.
- `make_qa_policy(name)` to resolve QA policy through registry.
- `make_sidecar_runner(plugin="custom_sidecar")` to inject a sidecar runner (env MA_SIDECAR_PLUGIN also supported).
"""
from __future__ import annotations

import os
from typing import Optional, Callable
from pathlib import Path

from ma_audio_engine.adapters_src import service_registry
from ma_audio_engine.adapters.cache_adapter import CacheAdapter
from ma_audio_engine.adapters_src import plugin_loader

__all__ = [
    "make_logger",
    "make_cache",
    "make_qa_policy",
    "make_sidecar_runner",
]


def make_logger(prefix: str, *, structured: bool = False, defaults: Optional[dict] = None, **kwargs):
    """Return a plain or structured logger via service_registry (no-op plugins handled there)."""
    if structured or kwargs.get("log_json"):
        return service_registry.get_structured_logger(prefix, defaults=defaults)
    return service_registry.get_logger(prefix, redact=kwargs.get("redact"), secrets=kwargs.get("secrets"))


def make_cache(cache_dir: Optional[str], backend: Optional[str] = None, *, plugin: Optional[str] = None) -> CacheAdapter:
    """
    Return a cache adapter, optionally overridden by a plugin.
    Plugin discovery:
      - explicit `plugin` arg
      - env MA_CACHE_PLUGIN
    """
    plugin_name = plugin or os.getenv("MA_CACHE_PLUGIN")
    if plugin_name:
        factory = plugin_loader.load_factory("cache", plugin_name)
        if factory:
            try:
                return factory(cache_dir=cache_dir, backend=backend)  # type: ignore
            except Exception:
                # fall back to default on plugin failure
                pass
    return service_registry.get_cache(cache_dir, backend=backend)


def make_qa_policy(name: str):
    return service_registry.get_qa_policy(name)


def make_sidecar_runner(custom_runner: Optional[Callable] = None, *, plugin: Optional[str] = None) -> Callable:
    """
    Sidecar runner factory with optional plugin override.
    Plugin discovery:
      - explicit `plugin` arg
      - env MA_SIDECAR_PLUGIN
    """
    if custom_runner:
        return custom_runner
    plugin_name = plugin or os.getenv("MA_SIDECAR_PLUGIN")
    if plugin_name:
        factory = plugin_loader.load_factory("sidecar", plugin_name)
        if factory:
            try:
                return factory()
            except Exception:
                pass
    # Default no-op runner; real sidecar invocation lives in sidecar_adapter.
    def _noop(*args, **kwargs):
        raise NotImplementedError("sidecar runner not injected")
    return _noop
