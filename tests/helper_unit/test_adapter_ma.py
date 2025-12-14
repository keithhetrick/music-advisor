from pathlib import Path

from ma_helper.adapters import get_adapter


def test_ma_orchestrator_adapter_loads_stub(tmp_path: Path, monkeypatch):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    orch_path = tools_dir / "ma_orchestrator.py"
    orch_path.write_text(
        """
def load_projects():
    return {"demo": type("P", (), {"name": "demo", "type": "test", "path": "x", "tests": [], "deps": [], "run": None})()}
def list_projects(projects):
    return 0
def print_deps(projects, reverse=False):
    return 0
def run_tests_for_project(project):
    return 0
def run_project_target(project):
    return 0
def run_affected_tests(projects, base):
    return 0
"""
    )
    adapter_factory = get_adapter("ma_orchestrator")
    adapter = adapter_factory(tmp_path)
    projects = adapter.load_projects()
    assert "demo" in projects
    assert adapter.list_projects(projects) == 0
    assert adapter.print_deps(projects) == 0
