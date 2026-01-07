"""Shim delegating to engines.ttc_engine.tools.ttc_summarize."""
from engines.ttc_engine.tools.ttc_summarize import (
    decade,
    fetch_corpus,
    fetch_local,
    fmt,
    main,
    parse_args,
    percentile,
    print_summary,
    summarize,
    summarize_decades,
    table_exists,
)

__all__ = [
    "decade",
    "fetch_corpus",
    "fetch_local",
    "fmt",
    "main",
    "parse_args",
    "percentile",
    "print_summary",
    "summarize",
    "summarize_decades",
    "table_exists",
]
