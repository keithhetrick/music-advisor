import json
from pathlib import Path

try:  # Py3.11+ stdlib
    import tomllib as tomli
except ModuleNotFoundError:
    import tomli  # type: ignore[no-redef]


def test_console_scripts_present_and_importable():
    pyproject = tomli.loads(Path("pyproject.toml").read_text())
    scripts = pyproject.get("project", {}).get("scripts", {})
    allowed = {"ma": "ma_helper.cli:main", "ma-helper": "ma_helper.cli:main"}
    assert scripts == allowed, "Root console scripts should only expose ma/ma-helper entrypoints"
