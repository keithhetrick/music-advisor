"""Adapter that wraps the existing tools/ma_orchestrator.py module."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Dict

from ma_helper.core.adapters import OrchestratorAdapter, Project
from ma_helper.core.env import ROOT


class MaOrchestratorAdapter(OrchestratorAdapter):
    def __init__(self, orch_path: Path | None = None) -> None:
        self._orch_path = orch_path or ROOT / "tools" / "ma_orchestrator.py"
        self._orch = self._load_orch()
        self.ROOT = getattr(self._orch, "ROOT", self._orch_path.parent.parent)

    def _load_orch(self):
        spec = importlib.util.spec_from_file_location("ma_orchestrator", self._orch_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load ma_orchestrator.py")
        orch = importlib.util.module_from_spec(spec)
        sys.modules["ma_orchestrator"] = orch
        spec.loader.exec_module(orch)
        return orch

    def load_projects(self) -> Dict[str, Project]:
        return self._orch.load_projects()

    def list_projects(self, projects: Dict[str, Project]) -> int:
        return self._orch.list_projects(projects)

    def print_deps(self, projects: Dict[str, Project], *, reverse: bool = False) -> int:
        return self._orch.print_deps(projects, reverse=reverse)

    def run_tests_for_project(self, project: Project) -> int:
        return self._orch.run_tests_for_project(project)

    def run_project_target(self, project: Project) -> int:
        return self._orch.run_project_target(project)

    def run_affected_tests(self, projects: Dict[str, Project], base: str) -> int:
        return self._orch.run_affected_tests(projects, base)

    def resolve_project_arg(self, projects: Dict[str, Project], arg: str, default=None) -> Project:
        if hasattr(self._orch, "resolve_project_arg"):
            return self._orch.resolve_project_arg(projects, arg, default)
        # Simple fallback: exact match or by name prefix
        if arg in projects:
            return projects[arg]
        for name in projects:
            if name.startswith(arg):
                return projects[name]
        if default and default in projects:
            return projects[default]
        raise KeyError(f"Project '{arg}' not found")


def get_adapter(root: Path | None = None) -> OrchestratorAdapter:
    orch_path = None
    if root is not None:
        orch_path = Path(root) / "tools" / "ma_orchestrator.py"
    return MaOrchestratorAdapter(orch_path)
