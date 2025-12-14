"""Task graph + cache abstraction stubs for future Turbo/Nx-style orchestration.

This is a placeholder module to start defining tasks/outputs and pluggable caches.
We keep it lightweight and import-free so other repos can extend it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Protocol, runtime_checkable, Any


@dataclass
class OutputSpec:
    """Represents a declared output (file/dir) for a task."""

    path: Path
    cache_key: str | None = None


@dataclass
class TaskSpec:
    """Represents a task and its declared inputs/outputs."""

    name: str
    command: str
    inputs: List[Path] = field(default_factory=list)
    outputs: List[OutputSpec] = field(default_factory=list)
    deps: List[str] = field(default_factory=list)


@runtime_checkable
class CacheBackend(Protocol):
    """Minimal cache backend interface; real implementations can plug in."""

    def fetch(self, key: str, dest: Path) -> bool: ...
    def store(self, key: str, src: Path) -> bool: ...


class LocalCache(CacheBackend):
    """Stub local cache (no-op) to be replaced by real cache providers."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def fetch(self, key: str, dest: Path) -> bool:
        # TODO: implement file copy from cache root/key -> dest
        return False

    def store(self, key: str, src: Path) -> bool:
        # TODO: implement file copy src -> cache root/key
        return False


def build_task_graph(specs: Dict[str, TaskSpec]) -> Dict[str, TaskSpec]:
    """Return validated task specs (placeholder)."""
    # Future: topo-validate, detect cycles, normalize paths.
    return specs


def load_task_specs(data: Dict[str, Any], root: Path) -> Dict[str, TaskSpec]:
    """
    Load tasks from a config dict (e.g., parsed TOML/JSON).
    Expected shape:
      tasks.<name>.command = "..."
      tasks.<name>.deps = ["taskA", ...]
      tasks.<name>.outputs = ["path/to/out", ...]
      tasks.<name>.inputs = ["path/to/in", ...]
    """
    specs: Dict[str, TaskSpec] = {}
    tasks_cfg = data.get("tasks", {})
    for name, cfg in tasks_cfg.items():
        cmd = cfg.get("command")
        if not cmd:
            continue
        deps = cfg.get("deps", []) or []
        inputs = [Path(p) if Path(p).is_absolute() else root / p for p in cfg.get("inputs", []) or []]
        outputs = [
            OutputSpec(Path(p) if Path(p).is_absolute() else root / p, cache_key=cfg.get("cache_key"))
            for p in cfg.get("outputs", []) or []
        ]
        specs[name] = TaskSpec(name=name, command=cmd, inputs=inputs, outputs=outputs, deps=deps)
    return specs
