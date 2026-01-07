"""Shim delegating to engines.ttc_engine.tools.ttc_extract_from_mcgill."""
from engines.ttc_engine.tools.ttc_extract_from_mcgill import (
    extract_rows,
    main,
    parse_args,
    write_csv,
    write_json,
)

__all__ = [
    "extract_rows",
    "main",
    "parse_args",
    "write_csv",
    "write_json",
]
