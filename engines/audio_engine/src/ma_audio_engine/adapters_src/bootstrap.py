"""Bootstrap helper to ensure repository paths are on sys.path (no legacy adapters dependency)."""
from __future__ import annotations

import sys
from pathlib import Path

from shared.config.paths import get_repo_root


def ensure_repo_root() -> None:
    """Insert repo root and project src paths on sys.path once if missing."""
    repo_root = get_repo_root().resolve()
    repo_str = str(repo_root)
    src_path = repo_root / "src"
    src_str = str(src_path)
    audio_engine_src = repo_root / "engines" / "audio_engine" / "src"
    audio_engine_str = str(audio_engine_src)
    lyrics_engine_src = repo_root / "engines" / "lyrics_engine" / "src"
    lyrics_engine_str = str(lyrics_engine_src)
    ttc_engine_src = repo_root / "engines" / "ttc_engine" / "src"
    ttc_engine_str = str(ttc_engine_src)
    host_core_src = repo_root / "hosts" / "advisor_host_core" / "src"
    host_core_str = str(host_core_src)

    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)

    if src_path.exists() and src_str not in sys.path:
        try:
            insert_at = sys.path.index(repo_str) + 1
        except ValueError:
            insert_at = 0
        sys.path.insert(insert_at, src_str)

    if audio_engine_src.exists() and audio_engine_str not in sys.path:
        sys.path.append(audio_engine_str)
    if lyrics_engine_src.exists() and lyrics_engine_str not in sys.path:
        sys.path.append(lyrics_engine_str)
    if ttc_engine_src.exists() and ttc_engine_str not in sys.path:
        sys.path.append(ttc_engine_str)
    if host_core_src.exists() and host_core_str not in sys.path:
        sys.path.append(host_core_str)


__all__ = ["ensure_repo_root"]
