"""
Wrapper namespace for lyric/STT tools (legacy modules under root tools/).

Extends __path__ to include the top-level tools directory so imports like
`ma_lyrics_engine.tools.lyric_wip_pipeline` resolve without copying all
modules.
"""
from __future__ import annotations

import pkgutil
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TOOLS_ROOT = _REPO_ROOT / "tools"

__path__ = pkgutil.extend_path(__path__, __name__)  # type: ignore[name-defined]
if _TOOLS_ROOT.exists():
    __path__.append(str(_TOOLS_ROOT))

__all__: list[str] = []
