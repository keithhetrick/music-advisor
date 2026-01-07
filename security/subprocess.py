"""
Compatibility wrapper: delegates to shared.security.subprocess (source of truth).
"""
from shared.security.subprocess import (
    SubprocessValidationError,
    run_safe,
)

__all__ = [
    "SubprocessValidationError",
    "run_safe",
]
