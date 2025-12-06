"""
File safety helpers: filename validation, allowed extensions, and size checks.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Optional

from shared.security.config import CONFIG, SecurityConfig


class FileValidationError(ValueError):
    """Raised when a file or filename fails validation."""


_FILENAME_BAD_CHARS = re.compile(r"[\\:*?\"<>|]")


def validate_filename(name: str) -> None:
    """
    Basic filename sanity: non-empty, no separators or shell-special bad chars.
    """
    if not name or name.strip() == "":
        raise FileValidationError("filename is empty")
    if "/" in name or "\0" in name:
        raise FileValidationError("filename contains path separators or null byte")
    if _FILENAME_BAD_CHARS.search(name):
        raise FileValidationError("filename contains forbidden characters")


def ensure_allowed_extension(
    name: str,
    allowed_exts: Optional[Iterable[str]] = None,
    *,
    config: SecurityConfig = CONFIG,
) -> None:
    """
    Ensure filename has an allowed extension (case-insensitive).
    """
    allowed = {ext.lower() for ext in (allowed_exts or config.allowed_exts)}
    ext = Path(name).suffix.lower()
    if ext not in allowed:
        raise FileValidationError(f"extension not allowed: {ext}")


def ensure_size_ok(path: Path, *, config: SecurityConfig = CONFIG) -> None:
    """
    Ensure file size does not exceed max_file_bytes.
    """
    size = os.path.getsize(path)
    if size > config.max_file_bytes:
        raise FileValidationError(f"file too large: {size} bytes (max {config.max_file_bytes})")


# Backward-compatible alias
def ensure_max_size(path: Path, max_bytes: int, *, config: SecurityConfig | None = None) -> None:
    """
    Legacy signature: ensure file <= max_bytes (ignores config defaults when provided explicitly).
    """
    cfg = config or CONFIG
    size = os.path.getsize(path)
    if size > max_bytes:
        raise FileValidationError(f"file too large: {size} bytes (max {max_bytes})")
