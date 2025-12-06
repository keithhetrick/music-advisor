"""
Repository-wide bootstrap to keep imports modular and avoid per-script sys.path hacks.

Python automatically imports ``sitecustomize`` when it is importable on ``sys.path``.
Because we typically launch tools from the repo root (or with the repo root on
``PYTHONPATH``), this file ensures the repository root is present on the import path
early in process startup. This lets all scripts import the shared ``adapters`` modules
without sprinkling ``sys.path.insert`` calls across the codebase.
"""

from __future__ import annotations

import pathlib
import sys


def _ensure_repo_root() -> None:
    root = pathlib.Path(__file__).resolve().parent
    root_str = str(root)
    src_path = root / "src"
    src_str = str(src_path)
    audio_engine_src = root / "engines" / "audio_engine" / "src"
    lyrics_engine_src = root / "engines" / "lyrics_engine" / "src"
    ttc_engine_src = root / "engines" / "ttc_engine" / "src"
    host_core_src = root / "hosts" / "advisor_host_core" / "src"

    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)

    if src_path.exists() and src_str not in sys.path:
        sys.path.insert(1, src_str)

    for extra in (audio_engine_src, lyrics_engine_src, ttc_engine_src, host_core_src):
        extra_str = str(extra)
        if extra.exists() and extra_str not in sys.path:
            sys.path.append(extra_str)


_ensure_repo_root()

# Alias legacy adapters package to the new ma_audio_engine.adapters for compatibility.
try:
    import ma_audio_engine.adapters as _ad
    sys.modules.setdefault("adapters", _ad)
except Exception:
    pass
