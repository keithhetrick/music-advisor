"""
Preflight adapter: lightweight validators to keep CLIs honest before work starts.
Shared across injectors/rankers to avoid bespoke path checks.

Usage:
- `validate_root_dir(root)` to confirm a folder exists (logs warnings otherwise).
- `validate_root_list("a,b,c")` for comma-separated roots.
- `ensure_parent_dir(path)` to create parent dirs for outputs.
- `require_paths([...])` to assert inputs exist before running heavy work.

Notes:
- Side effects: may create directories (`ensure_parent_dir`); otherwise read-only.
- Logging: accepts an optional logger callable for structured or plain logs; defaults to no-op.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, List, Optional

JsonLogger = Optional[Callable[[str], None]]


def _log(logger: JsonLogger) -> Callable[[str], None]:
    return logger or (lambda _msg: None)


def validate_root_dir(root: str | Path, logger: JsonLogger = None) -> Optional[Path]:
    """
    Ensure the provided root exists and is a directory. Returns the Path or None.
    """
    log = _log(logger)
    path = Path(root).expanduser()
    if not path.exists():
        log(f"[preflight] missing root: {path}")
        return None
    if not path.is_dir():
        log(f"[preflight] root is not a directory: {path}")
        return None
    return path


def validate_root_list(raw_roots: str, logger: JsonLogger = None) -> List[Path]:
    """
    Split a comma-separated root list and validate each directory.
    """
    paths: List[Path] = []
    for chunk in raw_roots.split(","):
        if not chunk.strip():
            continue
        valid = validate_root_dir(chunk.strip(), logger=logger)
        if valid:
            paths.append(valid)
    return paths


def ensure_parent_dir(path: str | Path, logger: JsonLogger = None) -> Path:
    """
    Create parent directories for a path (useful for outputs).
    """
    log = _log(logger)
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        log(f"[preflight] failed to create parent dir for {p}: {exc}")
    return p


def require_paths(paths: Iterable[str | Path], logger: JsonLogger = None) -> bool:
    """
    Ensure a collection of paths exist. Returns True only if all are present.
    """
    log = _log(logger)
    ok = True
    for path in paths:
        p = Path(path)
        if not p.exists():
            log(f"[preflight] missing path: {p}")
            ok = False
    return ok
