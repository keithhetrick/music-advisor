import json
from pathlib import Path

try:  # Py3.11+ stdlib
    import tomllib as tomli
except ModuleNotFoundError:
    import tomli  # type: ignore[no-redef]


def test_console_scripts_present_and_importable():
    pyproject = tomli.loads(Path("pyproject.toml").read_text())
    scripts = pyproject.get("project", {}).get("scripts", {})
    assert scripts == {}, "Root console scripts should be empty; use per-project scripts"
