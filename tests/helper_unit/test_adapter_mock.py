from pathlib import Path

from ma_helper.adapters import get_adapter


def test_mock_adapter_with_registry(tmp_path: Path):
    reg = {
        "demo": {"path": "demo", "type": "lib", "deps": ["dep1"], "tests": ["demo/tests"]},
        "dep1": {"path": "dep1", "type": "lib", "deps": [], "tests": []},
    }
    reg_path = tmp_path / "project_map.json"
    reg_path.write_text(__import__("json").dumps(reg))
    adapter_factory = get_adapter("mock")
    adapter = adapter_factory(tmp_path, reg_path)
    projects = adapter.load_projects()
    assert "demo" in projects and "dep1" in projects
    assert adapter.list_projects(projects) == 0
    assert adapter.print_deps(projects) == 0
    assert adapter.run_tests_for_project(projects["demo"]) == 0
    assert adapter.run_project_target(projects["demo"]) == 0
    assert adapter.run_affected_tests(projects, "origin/main") == 0
