"""
Script-facing defaults for env vars used by shell wrappers.

Purpose:
- Keep Automator/shell wrapper defaults centralized (repo name, python path, lyric profiles).
- Make it easy for scripts to import a single source of truth instead of duplicating literals.

Usage:
- Import and reference in shell/Python wrappers: e.g., `DEFAULT_PYTHON` for `.venv/bin/python`.
- Lyric profiles are passed through Automator scripts to downstream lyric tools.
"""
from __future__ import annotations

DEFAULT_REPO_ENV = "music-advisor"
DEFAULT_PYTHON = ".venv/bin/python"

# Lyric profiles (env passed through scripts)
DEFAULT_LYRIC_LCI_PROFILE = "lci_us_pop_v1"
DEFAULT_LYRIC_LCI_CALIBRATION = "calibration/lci_calibration_us_pop_v1.json"

__all__ = [
    "DEFAULT_REPO_ENV",
    "DEFAULT_PYTHON",
    "DEFAULT_LYRIC_LCI_PROFILE",
    "DEFAULT_LYRIC_LCI_CALIBRATION",
]
