#!/usr/bin/env python3
"""
Policy Bypass Helper

Reads a client.txt from STDIN or a file path and prints a modified version to STDOUT
that forces:
  use_ttc=true | use_exposures=true
(Non-destructive: you can redirect output to a new file.)
"""
import sys, re

def force_flag(line: str, key: str) -> str:
    # replace key=value within the STRUCTURE_POLICY line; add if missing
    if "STRUCTURE_POLICY" not in line:
        return line
    if key in line:
        return re.sub(rf"{key}\s*=\s*false", f"{key}=true", line)
    # append if not present
    if line.strip().endswith("\\"):
        return line + f" {key}=true"
    return line + f" | {key}=true"

def transform(text: str) -> str:
    out = []
    for ln in text.splitlines():
        if "STRUCTURE_POLICY" in ln:
            ln = force_flag(ln, "use_ttc")
            ln = force_flag(ln, "use_exposures")
        out.append(ln)
    return "\n".join(out)

def main():
    if len(sys.argv) == 2:
        txt = open(sys.argv[1], "r", encoding="utf-8", errors="ignore").read()
    else:
        txt = sys.stdin.read()
    print(transform(txt))

if __name__ == "__main__":
    main()
