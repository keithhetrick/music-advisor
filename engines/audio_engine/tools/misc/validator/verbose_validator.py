#!/usr/bin/env python3
"""
Verbose Validator (Music Advisor v1.1 sidecar)

Modes:
  1) PACK + CLIENT paths  → full audit (preferred)
  2) PACK="-" + CLIENT    → read pack JSON from STDIN
  3) --policy-only CLIENT → policy snapshot without a pack

Prints LARGE JSON to STDOUT:
- raw ingest fields
- normalized values
- influence_map (expected HCI subdomains)
- status: used/ignored (and why)
- Known_Gaps (expected but missing)
- policy_snapshot
"""
import json, re, sys
from pathlib import Path

FIELD_INFLUENCE = {
    "region": ["Market"],
    "runtime_sec": ["Market"],
    "tempo_bpm": ["Sonic","Historical"],
    "tempo_band_bpm": ["Sonic","Market"],
    "ttc_sec": ["Emotional","Market"],
    "exposures": ["Market","Historical"],
    "sections": ["Historical","Creative"],
    "hook_positions": ["Emotional","Market"],
    "rhythm_features": ["Sonic","Creative"],
    "production_features": ["Sonic"],
    "tonal_features": ["Sonic","Historical","Cultural"],
    "era_refs": ["Historical"],
    "production_tags": ["Creative"],
    "MARKET_NORMS.profile": ["Market"]
}

def parse_policy(client_txt: str):
    sp = {
        "mode": ("strict" if "mode=strict" in client_txt.lower()
                 else ("optional" if "mode=optional" in client_txt.lower() else None)),
        "reliable": "reliable=true" in client_txt.lower(),
        "use_ttc": "use_ttc=true" in client_txt.lower(),
        "use_exposures": "use_exposures=true" in client_txt.lower(),
    }
    pri_m = re.search(r"priors\s*=\s*\{([^}]+)\}", client_txt, re.IGNORECASE)
    cap_m = re.search(r"caps\s*=\s*\{([^}]+)\}", client_txt, re.IGNORECASE)
    gp = {
        "active": "GOLDILOCKS_POLICY: active=true" in client_txt,
        "priors_raw": pri_m.group(1) if pri_m else None,
        "caps_raw": cap_m.group(1) if cap_m else None
    }
    return {"STRUCTURE_POLICY": sp, "GOLDILOCKS_POLICY": gp}

def norm_num(x):
    try: return float(x)
    except Exception: return x

def normalize_field(name, raw):
    if raw is None:
        return None
    if name in ("ttc_sec","runtime_sec","tempo_bpm"):
        return norm_num(raw)
    if name == "tempo_band_bpm" and isinstance(raw, str) and ("–" in raw or "-" in raw):
        sep = "–" if "–" in raw else "-"
        parts = [p.strip() for p in raw.split(sep)]
        if len(parts) == 2:
            try:
                lo, hi = float(parts[0]), float(parts[1])
                return {"lo": lo, "hi": hi, "centroid": (lo+hi)/2.0}
            except Exception:
                return raw
    return raw

def build_verbose(pack: dict, client_txt: str):
    policies = parse_policy(client_txt)
    report = {
        "pack_id": pack.get("track_id") or pack.get("id") or None,
        "policy_snapshot": policies,
        "fields": {},
        "Known_Gaps": []
    }
    def put(name, value, source="ingest"):
        info = {
            "raw": value,
            "normalized": normalize_field(name, value),
            "provenance": source,
            "influence_map": FIELD_INFLUENCE.get(name, ["Unknown"])
        }
        if name == "ttc_sec" and not policies["STRUCTURE_POLICY"]["use_ttc"]:
            info["status"] = "ignored (STRUCTURE_POLICY.use_ttc=false)"
            info["confidence"] = 0.0
        elif name == "exposures" and not policies["STRUCTURE_POLICY"]["use_exposures"]:
            info["status"] = "ignored (STRUCTURE_POLICY.use_exposures=false)"
            info["confidence"] = 0.0
        else:
            info["status"] = "used"
            info["confidence"] = 0.9
        report["fields"][name] = info

    # MARKET_NORMS.profile (flatten if present)
    if isinstance(pack.get("MARKET_NORMS"), dict) and "profile" in pack["MARKET_NORMS"]:
        put("MARKET_NORMS.profile", pack["MARKET_NORMS"]["profile"])
    else:
        report["Known_Gaps"].append("MARKET_NORMS.profile")

    # simple keys
    for k in ["region","runtime_sec","tempo_bpm","tempo_band_bpm","ttc_sec","exposures"]:
        if k in pack:
            put(k, pack[k])
        else:
            report["Known_Gaps"].append(k)

    # buckets
    for b in ["sections","hook_positions","rhythm_features","production_features","tonal_features","era_refs","production_tags"]:
        if b in pack:
            put(b, pack[b])
        else:
            report["Known_Gaps"].append(b)

    # finalize gaps (exclude ones we actually added)
    report["Known_Gaps"] = sorted(set([g for g in report["Known_Gaps"] if g not in report["fields"]]))
    return report

def main(argv):
    if len(argv) >= 2 and argv[1] == "--policy-only":
        if len(argv) != 3:
            print("Usage: verbose_validator.py --policy-only path/to/client.txt", file=sys.stderr)
            sys.exit(1)
        client_txt = Path(argv[2]).read_text()
        print(json.dumps({"policy_snapshot": parse_policy(client_txt)}, indent=2))
        return

    if len(argv) < 3:
        print("Usage: verbose_validator.py <pack.json|-> <client.txt>", file=sys.stderr)
        sys.exit(1)

    pack_arg, client_path = argv[1], argv[2]
    client_txt = Path(client_path).read_text()
    if pack_arg == "-":
        # read pack JSON from STDIN
        pack = json.loads(sys.stdin.read())
    else:
        pack = json.loads(Path(pack_arg).read_text())
    print(json.dumps(build_verbose(pack, client_txt), indent=2))

if __name__ == "__main__":
    main(sys.argv)
