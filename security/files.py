"""
Compatibility wrapper: delegates to shared.security.files (source of truth).
"""
from shared.security.files import (
    FileValidationError,
    validate_filename,
    ensure_allowed_extension,
    ensure_size_ok,
    ensure_max_size,
)

__all__ = [
    "FileValidationError",
    "validate_filename",
    "ensure_allowed_extension",
    "ensure_size_ok",
    "ensure_max_size",
]
