"""Shim delegating to engines.ttc_engine.tools.ttc_init_db."""
from engines.ttc_engine.tools.ttc_init_db import (
    ensure_db,
    init_tables,
    main,
    parse_args,
)

__all__ = [
    "ensure_db",
    "init_tables",
    "main",
    "parse_args",
]
