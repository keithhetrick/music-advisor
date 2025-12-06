"""
DB safety helpers: identifier validation and parameterization guidance.
"""
from __future__ import annotations

import re
from typing import Iterable


class DBSecurityError(ValueError):
    """Raised when SQL identifier validation fails."""


_IDENT_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_table_name(name: str, allowed: Iterable[str] | None = None) -> str:
    """
    Ensure a table name is a simple identifier and optionally in an allowlist.
    Returns the validated name for convenience.
    """
    if not name or not _IDENT_RX.match(name):
        raise DBSecurityError(f"unsafe table name: {name!r}")
    if allowed is not None:
        allowed_set = {t for t in allowed}
        if name not in allowed_set:
            raise DBSecurityError(f"table not allowed: {name}")
    return name


def safe_execute(conn, sql: str, params: Iterable | None = None):
    """
    Thin wrapper to encourage parameterized queries and consistent behavior.
    - params must be None or an iterable (tuple/list recommended).
    - Does not attempt to sanitize SQL; caller must validate identifiers.
    """
    if params is None:
        return conn.execute(sql)
    if isinstance(params, (str, bytes)):
        raise DBSecurityError("params must not be a string; use a tuple/list of parameters")
    return conn.execute(sql, tuple(params))
