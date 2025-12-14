"""Adapters for project inventory and orchestration, to make the helper pluggable."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterable, Protocol


class Project(Protocol):
    name: str
    type: str
    path: Path
    tests: Iterable[str] | None
    deps: Iterable[str] | None
    run: Any


class OrchestratorAdapter(ABC):
    """Abstract orchestrator interface so ma_helper can swap implementations."""

    @abstractmethod
    def load_projects(self) -> Dict[str, Project]:
        ...

    @abstractmethod
    def list_projects(self, projects: Dict[str, Project]) -> int:
        ...

    @abstractmethod
    def print_deps(self, projects: Dict[str, Project], *, reverse: bool = False) -> int:
        ...

    @abstractmethod
    def run_tests_for_project(self, project: Project) -> int:
        ...

    @abstractmethod
    def run_project_target(self, project: Project) -> int:
        ...

    @abstractmethod
    def run_affected_tests(self, projects: Dict[str, Project], base: str) -> int:
        ...
