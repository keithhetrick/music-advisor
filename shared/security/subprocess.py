"""
Subprocess safety helpers: enforce shell=False and optional binary allowlists.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional
from shared.security.config import CONFIG, SecurityConfig


class SubprocessValidationError(ValueError):
    """Raised when a subprocess command fails validation."""


def _is_allowed_binary(binary: str, allowlist_roots: Iterable[Path]) -> bool:
    """
    Resolve a binary and ensure it lives under one of the allowed roots.
    """
    resolved = Path(shutil.which(binary) or binary).expanduser().resolve()
    return any(str(resolved).startswith(str(root)) for root in allowlist_roots)


def run_safe(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
    allow_roots: Optional[Iterable[Path]] = None,
    check: bool = True,
    capture_output: bool = False,
    text: bool = True,
    env: Optional[dict] = None,
    config: SecurityConfig = CONFIG,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess with shell=False and an optional binary allowlist.
    """
    if not cmd:
        raise SubprocessValidationError("empty command")
    roots = [Path(r).expanduser().resolve() for r in (allow_roots or config.allowed_binary_roots)]
    if not _is_allowed_binary(cmd[0], roots):
        raise SubprocessValidationError(f"binary not allowed: {cmd[0]}")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        timeout=timeout if timeout is not None else config.subprocess_timeout,
        check=check,
        capture_output=capture_output,
        text=text if capture_output else False,
        env=env,
    )


__all__ = [
    "SubprocessValidationError",
    "run_safe",
]
