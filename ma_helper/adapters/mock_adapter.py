"""Mock adapter for demos/tests when no orchestrator is available."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from ma_helper.core.adapters import OrchestratorAdapter, Project
from ma_helper.core.registry import load_registry, load_registry_from_path


class MockAdapter(OrchestratorAdapter):
    def __init__(self, root: Path | None = None, registry_path: Path | None = None) -> None:
        self.root = Path(root or ".").resolve()
        self.registry_path = registry_path or (self.root / "project_map.json")
        self.ROOT = self.root

    def load_projects(self) -> Dict[str, Project]:
        reg = load_registry() if self.registry_path is None else load_registry_from_path(self.registry_path)
        return {
            name: type(
                "P",
                (),
                {
                    "name": name,
                    "type": meta.get("type", "misc"),
                    "path": Path(meta.get("path", ".")),
                    "tests": meta.get("tests", []),
                    "deps": meta.get("deps", []),
                    "run": meta.get("run"),
                },
            )()
            for name, meta in reg.items()
        }

    def list_projects(self, projects: Dict[str, Project]) -> int:
        for name in sorted(projects.keys()):
            print(name)
        return 0

    def print_deps(self, projects: Dict[str, Project], *, reverse: bool = False) -> int:
        if reverse:
            # naive reverse deps
            rev = {name: [] for name in projects}
            for name, proj in projects.items():
                for dep in getattr(proj, "deps", []) or []:
                    rev.setdefault(dep, []).append(name)
            for name, deps in rev.items():
                print(f"{name}: {', '.join(deps) or 'none'}")
        else:
            for name, proj in projects.items():
                deps = getattr(proj, "deps", []) or []
                print(f"{name}: {', '.join(deps) or 'none'}")
        return 0

    def run_tests_for_project(self, project: Project) -> int:
        print(f"[mock] test {project.name}")
        return 0

    def run_project_target(self, project: Project) -> int:
        print(f"[mock] run {project.name}")
        return 0

    def run_affected_tests(self, projects: Dict[str, Project], base: str) -> int:
        print(f"[mock] affected vs {base}: {', '.join(sorted(projects.keys()))}")
        return 0

    def resolve_project_arg(self, projects: Dict[str, Project], arg: str, default=None) -> Project:
        if arg in projects:
            return projects[arg]
        for name in projects:
            if name.startswith(arg):
                return projects[name]
        if default and default in projects:
            return projects[default]
        raise KeyError(f"Project '{arg}' not found")


def get_adapter(root: Path | None = None, registry_path: Path | None = None) -> OrchestratorAdapter:
    return MockAdapter(root, registry_path)
