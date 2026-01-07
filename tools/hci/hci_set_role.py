"""Shim delegating to engines.audio_engine.tools.hci.hci_set_role."""
from engines.audio_engine.tools.hci.hci_set_role import (
    load_hci,
    main,
    save_hci,
    set_role_for_file,
    set_role_for_root,
)

__all__ = [
    "load_hci",
    "main",
    "save_hci",
    "set_role_for_file",
    "set_role_for_root",
]
