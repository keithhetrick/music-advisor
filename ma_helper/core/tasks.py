"""Task graph + cache abstraction stubs for future Turbo/Nx-style orchestration.

This is a placeholder module to start defining tasks/outputs and pluggable caches.
We keep it lightweight and import-free so other repos can extend it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Protocol, runtime_checkable, Any
import hashlib
import os
import shutil
import tarfile
import tempfile
import time
from urllib.parse import urlparse


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
        cached = self.root / key / dest
        if not cached.exists():
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(cached, dest)
            return True
        except Exception:
            return False

    def store(self, key: str, src: Path) -> bool:
        try:
            dst = self.root / key / src
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return True
        except Exception:
            return False


class RemoteCache(CacheBackend):
    """Remote cache stub; extend with S3/Redis/etc. as needed."""

    def __init__(self, endpoint: str, root: Path) -> None:
        self.endpoint = endpoint
        self.root = root

    def fetch(self, key: str, dest: Path) -> bool:
        # Placeholder: implement real fetch from endpoint
        return False

    def store(self, key: str, src: Path) -> bool:
        # Placeholder: implement real store to endpoint
        return False


class S3Cache(CacheBackend):
    """S3-backed cache for task outputs."""

    def __init__(self, url: str, root: Path) -> None:
        self.root = root
        parsed = urlparse(url)
        if parsed.scheme != "s3" or not parsed.netloc:
            raise ValueError("S3 cache URL must be s3://bucket/prefix")
        self.bucket = parsed.netloc
        self.prefix = parsed.path.strip("/")
        try:
            import boto3
        except Exception as exc:
            raise RuntimeError("boto3 is required for S3 cache; pip install boto3") from exc
        self.s3 = boto3.client("s3")

    def _key(self, cache_key: str, path: Path) -> str:
        rel = path
        if path.is_absolute():
            rel = path.relative_to(self.root)
        rel_str = rel.as_posix()
        prefix = f"{self.prefix}/{cache_key}" if self.prefix else cache_key
        return f"{prefix}/{rel_str}"

    def fetch(self, key: str, dest: Path) -> bool:
        if dest.is_dir():
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        obj_key = self._key(key, dest)
        for _ in range(2):
            try:
                self.s3.download_file(self.bucket, obj_key, str(dest))
                return True
            except Exception:
                time.sleep(0.2)
        return False

    def store(self, key: str, src: Path) -> bool:
        if not src.exists() or src.is_dir():
            return False
        obj_key = self._key(key, src)
        for _ in range(2):
            try:
                self.s3.upload_file(str(src), self.bucket, obj_key)
                return True
            except Exception:
                time.sleep(0.2)
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


def topo_order(specs: Dict[str, TaskSpec], target: str) -> List[TaskSpec]:
    """Return dependency-respecting order for the target task."""
    order: List[TaskSpec] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(name: str):
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"Cycle detected at task '{name}'")
        if name not in specs:
            raise KeyError(f"Task '{name}' not found")
        visiting.add(name)
        for dep in specs[name].deps:
            dfs(dep)
        visiting.remove(name)
        visited.add(name)
        order.append(specs[name])

    dfs(target)
    return order


def outputs_fresh(task: TaskSpec) -> bool:
    """Heuristic: outputs exist and are newer than inputs."""
    if not task.outputs:
        return False
    outs = [o.path for o in task.outputs if o.path.exists()]
    if len(outs) != len(task.outputs):
        return False
    newest_in = max((p.stat().st_mtime for p in task.inputs), default=0)
    oldest_out = min((p.stat().st_mtime for p in outs), default=0)
    return oldest_out >= newest_in


def hash_inputs(task: TaskSpec) -> str:
    """Hash command + input paths + mtimes/sizes (fast, not content-perfect)."""
    h = hashlib.sha256()
    h.update(task.command.encode())
    for p in sorted(task.inputs):
        try:
            st = p.stat()
            h.update(str(p).encode())
            h.update(str(st.st_mtime_ns).encode())
            h.update(str(st.st_size).encode())
        except FileNotFoundError:
            h.update(str(p).encode())
            h.update(b"missing")
    return h.hexdigest()


def pack_outputs(task: TaskSpec, cache_key: str, root: Path) -> Path | None:
    """Create a tarball of declared outputs; returns path or None if no outputs."""
    if not task.outputs:
        return None
    temp_dir = Path(tempfile.mkdtemp())
    tar_path = temp_dir / f"{task.name}-{cache_key}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        for out in task.outputs:
            if out.path.exists():
                tar.add(out.path, arcname=str(out.path.relative_to(root)))
    return tar_path


def unpack_outputs(tar_path: Path, root: Path) -> bool:
    """Extract outputs tarball into root."""
    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=root)
        return True
    except Exception:
        return False
