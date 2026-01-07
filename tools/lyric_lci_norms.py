"""Compatibility shim delegating to engines.lyrics_engine.tools.lyric_lci_norms."""
from engines.lyrics_engine.tools.lyric_lci_norms import (
    parse_args,
    main,
)

__all__ = [
    "parse_args",
    "main",
]
