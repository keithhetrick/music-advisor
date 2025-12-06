"""
Plugin interface hints for optional extensions.

These are lightweight Protocols / type hints only; implementations are discovered
via adapters.plugin_loader (plugins/<kind>/<name>.py with a callable `factory`).
"""
from __future__ import annotations

from typing import Protocol, Callable, Optional, Dict, Any


class StructuredLogger(Protocol):
    def __call__(self, event: str, fields: Optional[Dict[str, Any]] = None) -> None: ...


class StructuredLoggerFactory(Protocol):
    def __call__(self, prefix: str = "", defaults: Optional[Dict[str, Any]] = None) -> StructuredLogger: ...


class SidecarRunner(Protocol):
    def __call__(self, audio: str, out: str, **kwargs) -> int: ...


class SidecarRunnerFactory(Protocol):
    def __call__(self) -> SidecarRunner: ...


class CacheFactory(Protocol):
    def __call__(self, cache_dir: Optional[str] = None, backend: Optional[str] = None): ...


class Exporter(Protocol):
    def __call__(self, payload: dict, path) -> None: ...


class CacheAdapterFactory(Protocol):
    def __call__(self, cache_dir: Optional[str] = None, backend: Optional[str] = None): ...


class CacheAdapter(Protocol):
    def load(self, *args, **kwargs): ...
    def store(self, *args, **kwargs): ...
