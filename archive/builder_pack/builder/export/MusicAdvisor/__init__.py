"""
Compatibility shim so legacy imports like `from MusicAdvisor ...` resolve.

- Forwards `MusicAdvisor` → `music_advisor` (lowercase PEP-8 package).
- If a top-level `Core` package/module exists, exposes it as `MusicAdvisor.Core`
  so existing tests stay working.

Safe to keep until you normalize imports.
"""
from __future__ import annotations
import importlib, sys

# Forward lowercase host package
try:
    _ma = importlib.import_module("music_advisor")
    sys.modules.setdefault("MusicAdvisor", _ma)
except Exception:
    pass

# Optionally forward a top-level Core package/module if it exists
try:
    _core = importlib.import_module("Core")
    sys.modules.setdefault("MusicAdvisor.Core", _core)
except Exception:
    pass
