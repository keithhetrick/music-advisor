"""Registry (project_map) helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .env import ROOT


def load_registry() -> Dict[str, Any]:
    project_map = ROOT / "project_map.json"
    if not project_map.exists():
        raise FileNotFoundError(f"project_map.json not found at {project_map}")
    return json.loads(project_map.read_text())


def load_registry_from_path(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"project_map.json not found at {path}")
    return json.loads(path.read_text())


def filter_projects(projects: Dict[str, Any], substr: str | None) -> Dict[str, Any]:
    if not substr:
        return projects
    substr = substr.lower()
    return {k: v for k, v in projects.items() if substr in k.lower() or substr in v.get("path", "").lower()}
