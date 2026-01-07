import re
from pathlib import Path


FORBIDDEN_PATTERNS = (
    re.compile(r"^\s*(from|import)\s+tools(\.|$)"),
    re.compile(r"^\s*(from|import)\s+ma_helper(\.|$)"),
    re.compile(r'importlib\.import_module\("tools\.'),  # hidden proxies
    re.compile(r'import_module\("tools\.'),
    re.compile(r'__import__\("tools\.'),
    re.compile(r'"tools\.'),  # string-based hooks
)

EXCLUDE_DIRS = {"archive", ".venv", "docs", "build", "dist", "archive/quarantine"}


def iter_engine_py_files():
    root = Path("engines")
    for path in root.rglob("*.py"):
        rel = path.relative_to(Path("."))
        if any(str(rel).startswith(f"{ex}/") or ex == str(rel) for ex in EXCLUDE_DIRS):
            continue
        parts = rel.parts
        if "src" not in parts:
            continue
        yield path


def test_engines_do_not_import_tools_or_ma_helper():
    violations = []
    for path in iter_engine_py_files():
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                for pat in FORBIDDEN_PATTERNS:
                    if pat.search(line):
                        violations.append(f"{path}:{lineno}:{line.strip()}")
    assert not violations, "Forbidden imports found:\n" + "\n".join(violations)
