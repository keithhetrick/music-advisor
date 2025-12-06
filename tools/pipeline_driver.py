#!/usr/bin/env python3
"""
Shim to ma_audio_engine.tools.pipeline_driver.
"""
from __future__ import annotations

def _resolve_pipeline_driver():
    try:
        from ma_audio_engine.tools.pipeline_driver import load_pipeline_config, main
        return load_pipeline_config, main
    except ImportError:
        # Fallback: ensure engine src is on sys.path if not already (direct invocation).
        import sys
        from pathlib import Path

        repo = Path(__file__).resolve().parents[1]
        engine_src = repo / "engines" / "audio_engine" / "src"
        sys.path.insert(0, str(repo))
        sys.path.insert(0, str(engine_src))
        from ma_audio_engine.tools.pipeline_driver import load_pipeline_config, main  # type: ignore
        return load_pipeline_config, main


load_pipeline_config, main = _resolve_pipeline_driver()

__all__ = ["load_pipeline_config", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
