"""
Tools package initializer.

Purpose:
- Allow tools modules/CLIs to be imported as a package (used by tests/import smoke).
- No runtime side effects; CLI entrypoints guard execution under __main__.

Docs:
- See tools/README.md for layout and guidance, and docs/COMMANDS.md for common entrypoints.

# Optional import logging to map live tool usage.
# Enable by setting MA_LOG_TOOL_IMPORTS=1; override log path via MA_TOOL_IMPORT_LOG.
"""

import os
import sys
from types import ModuleType
from typing import Optional

_LOG_IMPORTS = os.environ.get("MA_LOG_TOOL_IMPORTS") == "1"
_LOG_PATH = os.environ.get("MA_TOOL_IMPORT_LOG", "/tmp/ma_tool_imports.log")


def _log_import(name: str) -> None:
    """Append module import to a log file when enabled."""
    if not _LOG_IMPORTS:
        return
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"{name}\n")
    except Exception:
        pass


class _LoggingImporter:
    """Meta path hook to log tools.* imports when enabled."""

    def find_spec(self, fullname: str, path: Optional[list[str]], target: Optional[ModuleType] = None):
        if fullname == __name__ or not fullname.startswith(__name__ + "."):
            return None
        _log_import(fullname)
        return None  # Defer to normal import machinery


if _LOG_IMPORTS:
    sys.meta_path.insert(0, _LoggingImporter())
