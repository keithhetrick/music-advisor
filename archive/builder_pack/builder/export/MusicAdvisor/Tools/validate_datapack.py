#!/usr/bin/env python3
# validate_datapack.py - lightweight validator for MusicAdvisor DATA_PACKs
import json, sys, datetime

def validate(pack):
    problems = []
    # Required MVP fields
    required = ["region","generated_at","MARKET_NORMS","ttc_sec","runtime_sec","exposures","tempo_band_bpm"]
    for k in required:
        if k not in pack or pack[k] in (None, ""):
            problems.append(f"Missing required field: {k}")

    # Ranges (inline checks)
    def in_range(name, value, lo, hi):
        try:
            v = float(value)
            if not (lo <= v <= hi):
                problems.append(f"{name} out of range [{lo},{hi}]: {value}")
        except Exception:
            problems.append(f"{name} not a number: {value}")

    if "tempo_band_bpm" in pack: in_range("tempo_band_bpm", pack["tempo_band_bpm"], 40, 220)
    if "runtime_sec" in pack: in_range("runtime_sec", pack["runtime_sec"], 30, 480)
    if "ttc_sec" in pack: in_range("ttc_sec", pack["ttc_sec"], 0, 60)
    if "exposures" in pack:
        try:
            v = int(pack["exposures"])
            if not (1 <= v <= 10):
                problems.append(f"exposures out of range [1,10]: {v}")
        except Exception:
            problems.append(f"exposures not an integer: {pack['exposures']}")

    # MARKET_NORMS.profile required
    if "MARKET_NORMS" in pack:
        if not isinstance(pack["MARKET_NORMS"], dict) or not pack["MARKET_NORMS"].get("profile"):
            problems.append("MARKET_NORMS.profile is missing")
    else:
        problems.append("MARKET_NORMS missing")

    # generated_at ISO
    if "generated_at" in pack:
        try:
            datetime.datetime.fromisoformat(pack["generated_at"].replace("Z","+00:00"))
        except Exception:
            problems.append("generated_at is not ISO8601")

    return problems

def main():
    if len(sys.argv) != 2:
        print("Usage: validate_datapack.py <path_to_pack.json>")
        sys.exit(2)
    path = sys.argv[1]
    with open(path) as f:
        pack = json.load(f)
    probs = validate(pack)
    if probs:
        print("VALIDATION: FAIL")
        for p in probs:
            print(" -", p)
        sys.exit(1)
    else:
        print("VALIDATION: OK")
        sys.exit(0)

if __name__ == "__main__":
    main()
