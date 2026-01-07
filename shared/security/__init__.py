"""
Shared security surface (source of truth).
"""
from shared.security.config import (
    SecurityConfig,
    CONFIG,
)
from shared.security.paths import (
    PathValidationError,
    safe_join,
)
from shared.security.files import (
    FileValidationError,
    validate_filename,
    ensure_allowed_extension,
    ensure_size_ok,
    ensure_max_size,
)
from shared.security.db import (
    DBSecurityError,
    validate_table_name,
    safe_execute,
)
from shared.security.subprocess import (
    SubprocessValidationError,
    run_safe,
)

__all__ = [
    # config
    "SecurityConfig",
    "CONFIG",
    # paths
    "PathValidationError",
    "safe_join",
    # files
    "FileValidationError",
    "validate_filename",
    "ensure_allowed_extension",
    "ensure_size_ok",
    "ensure_max_size",
    # db
    "DBSecurityError",
    "validate_table_name",
    "safe_execute",
    # subprocess
    "SubprocessValidationError",
    "run_safe",
]
