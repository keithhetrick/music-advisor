"""Compatibility shim delegating to shared.ma_utils.philosophy_services."""
from shared.ma_utils.philosophy_services import (
    build_philosophy_line,
    inject_philosophy_into_hci,
    inject_philosophy_line_into_client,
    write_client_with_philosophy,
    write_hci_with_philosophy,
)

__all__ = [
    "build_philosophy_line",
    "inject_philosophy_into_hci",
    "inject_philosophy_line_into_client",
    "write_client_with_philosophy",
    "write_hci_with_philosophy",
]
