"""
Central contact helpers for Music Advisor.

Expose a single source of truth for contact emails so docs and code can
reference one place. Defaults to the primary studio address, but can be
overridden via environment for forks or white-label builds.
"""

from __future__ import annotations

import os


DEFAULT_CONTACT = "keith@bellweatherstudios.com"
DEFAULT_ALT = "info@bellweatherstudios.com"


def contact_email() -> str:
    """Return the primary contact email (env override allowed)."""
    return os.environ.get("MA_CONTACT_EMAIL", DEFAULT_CONTACT)


def alt_contact_email() -> str:
    """Return the alternate/general inbox (env override allowed)."""
    return os.environ.get("MA_CONTACT_ALT_EMAIL", DEFAULT_ALT)


__all__ = ["contact_email", "alt_contact_email", "DEFAULT_CONTACT", "DEFAULT_ALT"]
