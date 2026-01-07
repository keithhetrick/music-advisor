"""
Time adapter: central helper for generating UTC timestamps in a consistent format.

Usage:
- `utc_now_iso()` for ISO-8601 UTC timestamps with trailing Z (timespec=seconds default).

Notes:
- Pure helper (no side effects), intended for consistent timestamp formatting across logs/exports.
"""
from __future__ import annotations

from datetime import datetime

__all__ = [
    "utc_now_iso",
]


def utc_now_iso(timespec: str = "seconds") -> str:
    """
    Return current UTC time as ISO-8601 string with trailing 'Z'.
    """
    return datetime.utcnow().isoformat(timespec=timespec) + "Z"
