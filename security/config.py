"""
Compatibility wrapper: delegates to shared.security.config (source of truth).
"""
from shared.security.config import (
    SecurityConfig,
    CONFIG,
)

__all__ = [
    "SecurityConfig",
    "CONFIG",
]
