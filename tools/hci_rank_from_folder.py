#!/usr/bin/env python3
"""Compatibility shim: routes to tools/hci/hci_rank_from_folder.py"""
from tools.hci.hci_rank_from_folder import main

if __name__ == "__main__":
    raise SystemExit(main())
