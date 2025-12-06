#!/usr/bin/env python3
import json, sys
from difflib import unified_diff

if len(sys.argv) != 3:
    print("Usage: compare_runs.py <runA.json> <runB.json>")
    sys.exit(2)

with open(sys.argv[1], "r", encoding="utf-8") as fa:
    ja = json.load(fa)
with open(sys.argv[2], "r", encoding="utf-8") as fb:
    jb = json.load(fb)

print("HCI:", ja.get("hci", {}).get("score"), "vs", jb.get("hci", {}).get("score"))

for sect in ("advisory","optimization","promptsmith_bridge"):
    print(f"\n== {sect.upper()} ==")
    ta = (ja.get(sect, "") or "").splitlines()
    tb = (jb.get(sect, "") or "").splitlines()
    diff = unified_diff(ta, tb, fromfile=sys.argv[1], tofile=sys.argv[2], lineterm="")
    for line in diff:
        print(line)
