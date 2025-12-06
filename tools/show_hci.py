#!/usr/bin/env python3
# tools/show_hci.py
from __future__ import annotations
import json, sys

def main():
    if len(sys.argv) < 2:
        print("usage: python tools/show_hci.py <pack.json>")
        sys.exit(1)
    d = json.load(open(sys.argv[1]))
    final = (d.get("HCI") or {}).get("score")
    src = (d.get("HCI") or {}).get("source")
    raw = ((d.get("HCI_v1") or {}).get("HCI_v1_score"))
    if final is None:
        print("HCI not found in pack.")
        sys.exit(2)
    print(f"HCI = {final:.3f}  (source={src}; raw={raw:.3f})")

if __name__ == "__main__":
    main()
