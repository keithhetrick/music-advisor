"""Compatibility shim delegating to shared.ma_utils.echo_services."""
from shared.ma_utils.echo_services import (
    build_echo_header_line,
    build_hist_block,
    build_neighbor_lines,
    inject_echo_into_client,
    inject_echo_into_hci,
    trim_neighbors,
    write_neighbors_file,
)

__all__ = [
    "build_echo_header_line",
    "build_hist_block",
    "build_neighbor_lines",
    "inject_echo_into_client",
    "inject_echo_into_hci",
    "trim_neighbors",
    "write_neighbors_file",
]
