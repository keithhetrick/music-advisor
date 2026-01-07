"""
Compatibility wrapper: delegates to shared.security.paths (source of truth).
"""
from shared.security.paths import (
    PathValidationError,
    safe_join,
)

__all__ = [
    "PathValidationError",
    "safe_join",
]
