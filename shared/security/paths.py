"""
Path safety helpers: prevent traversal outside an allowed root.
"""
from __future__ import annotations

from pathlib import Path
from shared.security.config import CONFIG, SecurityConfig


class PathValidationError(ValueError):
    """Raised when a path fails validation (e.g., traversal outside base)."""


def safe_join(base: str | Path | None, user_path: str, *, config: SecurityConfig = CONFIG) -> Path:
    """
    Join user-supplied path to a base, normalize, and ensure it stays within base.

    Raises PathValidationError if the resulting path escapes the base.
    """
    base_path = Path(base or config.ingest_root).expanduser().resolve()
    candidate = (base_path / user_path).expanduser().resolve()
    try:
        candidate.relative_to(base_path)
    except ValueError as exc:
        raise PathValidationError(f"path escapes base: {candidate}") from exc
    return candidate
