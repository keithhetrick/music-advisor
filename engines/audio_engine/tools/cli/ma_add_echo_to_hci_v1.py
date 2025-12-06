#!/usr/bin/env python3
"""
Compatibility shim: routes to tools/hci/ma_add_echo_to_hci_v1.py
"""
from tools.hci.ma_add_echo_to_hci_v1 import main


if __name__ == "__main__":
    raise SystemExit(main())
