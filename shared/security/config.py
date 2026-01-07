"""
Central security configuration (trusted-only).

Values are overridable via environment variables at deploy time, not per-request.
Untrusted user input must never be used to set these.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, List, Set

from shared.config.paths import get_repo_root, get_features_output_root


def _split_exts(val: str | None, default: Iterable[str]) -> Set[str]:
    if not val:
        return {ext.lower() for ext in default}
    exts: Set[str] = set()
    for part in val.split(","):
        part = part.strip().lower()
        if not part:
            continue
        if not part.startswith("."):
            part = "." + part
        exts.add(part)
    return exts or {ext.lower() for ext in default}


def _split_paths(val: str | None, default: Iterable[Path]) -> List[Path]:
    if not val:
        return [p.expanduser().resolve() for p in default]
    parts = []
    for item in val.split(","):
        item = item.strip()
        if not item:
            continue
        parts.append(Path(item).expanduser().resolve())
    return parts or [p.expanduser().resolve() for p in default]


class SecurityConfig:
    def __init__(self) -> None:
        self.repo_root = get_repo_root()
        default_ingest = get_features_output_root()
        self.ingest_root = Path(
            os.environ.get("SECURITY_INGEST_ROOT", default_ingest)
        ).expanduser().resolve()
        max_mb = os.environ.get("SECURITY_MAX_FILE_MB", "1024")
        try:
            max_mb_int = int(max_mb)
        except Exception:
            max_mb_int = 1024
        self.max_file_bytes = max_mb_int * (1 << 20)
        default_exts = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".aif", ".aiff"}
        self.allowed_exts = _split_exts(os.environ.get("SECURITY_ALLOWED_EXTS"), default_exts)
        timeout = os.environ.get("SECURITY_SUBPROCESS_TIMEOUT", "120")
        try:
            self.subprocess_timeout = int(timeout)
        except Exception:
            self.subprocess_timeout = 120
        default_formats = {"wav", "mp3", "flac", "aac", "m4a", "ogg", "aiff", "aif"}
        self.allowed_formats = _split_exts(os.environ.get("SECURITY_ALLOWED_FORMATS"), default_formats)
        default_bin_roots = [
            self.repo_root,
            self.repo_root / ".venv" / "bin",
            Path("/usr/bin"),
            Path("/usr/local/bin"),
            Path("/opt/homebrew/bin"),
            Path("/usr/local/Cellar"),
            Path("/opt/homebrew/Cellar"),
            Path(sys.executable).expanduser().resolve().parent,
        ]
        self.allowed_binary_roots = _split_paths(os.environ.get("SECURITY_ALLOWED_BIN_ROOTS"), default_bin_roots)


CONFIG = SecurityConfig()

__all__ = [
    "SecurityConfig",
    "CONFIG",
]
