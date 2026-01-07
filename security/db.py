"""
Compatibility wrapper: delegates to shared.security.db (source of truth).
"""
from shared.security.db import (
    DBSecurityError,
    validate_table_name,
    safe_execute,
)

__all__ = [
    "DBSecurityError",
    "validate_table_name",
    "safe_execute",
]
