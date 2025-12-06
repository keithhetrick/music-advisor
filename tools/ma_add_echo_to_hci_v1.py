#!/usr/bin/env python3
"""Compatibility shim: routes to tools/hci/ma_add_echo_to_hci_v1.py"""
from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools.hci.ma_add_echo_to_hci_v1 import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
