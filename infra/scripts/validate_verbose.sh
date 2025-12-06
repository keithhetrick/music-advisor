#!/usr/bin/env python3
# Verbose Validator (adaptive) — macOS-friendly, schema-aware, sibling-enriched

import json, re, sys, os, glob
from pathlib import Path
from copy import deepcopy

# ------------------------------
# 1) Policy parsing
# ------------------------------
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

# ------------------------------
# 2) Field influence map (advisory)
# ------------------------------
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

EXPECTED_TOP = [
    "region","runtime_sec","tempo_bpm","tempo_band_bpm","ttc_sec","exposures",
    "sections","hook_positions","rhythm_features","production_features","tonal_features",
    "era_refs","production_tags","MARKET_NORMS.profile"
]

# ------------------------------
# 3) Schema adapter map (extend as needed)
#    Each v1.1 field -> list of candidate source keys (dotted for nested)
# ------------------------------
ADAPTER = {
    "runtime_sec": [
        "runtime_sec", "duration_sec", "duration", "analysis.duration_sec"
    ],
    "tempo_bpm": [
        "tempo_bpm", "tempoBpm", "analysis.tempo.bpm", "features.tempo_bpm_est"
    ],
    "tempo_band_bpm": [
        "tempo_band_bpm", "tempoBand", "tempo_range", "analysis.tempo.band"
    ],
    "ttc_sec": [
        "ttc_sec", "hook_time_sec", "hook_time", "chorus_time_sec", "chorus_time"
    ],
    "exposures": [
        "exposures", "hook_exposures", "chorus_count", "chorus_exposures"
    ],
    "sections": [
        "sections", "structure.sections", "analysis.sections"
    ],
    "hook_positions": [
        "hook_positions", "analysis.hook_positions", "hooks.positions"
    ],
    "rhythm_features": [
        "rhythm_features", "analysis.rhythm", "features.rhythm"
    ],
    "production_features": [
        "production_features", "analysis.production", "features.production",
        "mix.production_features"
    ],
    "tonal_features": [
        "tonal_features", "analysis.tonal", "features.tonal", "harmony.tonal_features"
    ],
    "era_refs": [
        "era_refs", "analysis.era_refs", "tags.eras"
    ],
    "production_tags": [
        "production_tags", "tags.production", "analysis.tags.production"
    ],
    "region": [
        "region", "market.region", "MARKET_NORMS.region", "meta.region"
    ],
    "MARKET_NORMS.profile": [
        "MARKET_NORMS.profile", "market.profile", "profile", "meta.profile"
    ],
}

# ------------------------------
# 4) Utility: deep get by dotted path
# ------------------------------
def deep_get(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur

# ------------------------------
# 5) Auto-enrichment: pull from sibling files if missing
# ------------------------------
def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return None

def sibling_candidates(pack_path):
    # look in the same folder for likely siblings
    p = Path(pack_path)
    folder = p.parent
    stem = p.stem.split(".pack")[0]  # strip trailing ".pack"
    # candidates ordered by usefulness
    patterns = [
        f"{stem}*.merged.json",
        f"{stem}*.features.json",
        f"{stem}*.beatlink.json",
        "*.merged.json",
        "*.features.json"
    ]
    out = []
    for pat in patterns:
        out.extend(sorted([str(x) for x in folder.glob(pat)]))
    # de-duplicate
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq

def merged_view(primary, extras):
    data = deepcopy(primary) if isinstance(primary, dict) else {}
    for ex in extras:
        if isinstance(ex, dict):
            # shallow merge for known buckets only
            for k in ["analysis","features","harmony","mix","tags","structure","market","MARKET_NORMS","meta"]:
                if k in ex and k not in data:
                    data[k] = ex[k]
    return data

# ------------------------------
# 6) Normalization helpers
# ------------------------------
def norm_num(x):
    try: return float(x)
    except Exception: return x

def normalize_field(name, raw):
    if raw is None:
        return None
    if name in ("ttc_sec","runtime_sec","tempo_bpm","exposures"):
        return norm_num(raw)
    if name == "tempo_band_bpm":
        # accept "120–129" or "120-129" or dict form already
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and ("–" in raw or "-" in raw):
            sep = "–" if "–" in raw else "-"
            parts = [p.strip() for p in raw.split(sep)]
            if len(parts) == 2:
                try:
                    lo, hi = float(parts[0]), float(parts[1])
                    return {"lo": lo, "hi": hi, "centroid": (lo+hi)/2.0}
                except Exception:
                    return raw
    return raw

# ------------------------------
# 7) Adapter: fill v1.1 fields from pack + siblings
# ------------------------------
def adapt_to_schema(pack_path):
    base = load_json(pack_path)
    if not isinstance(base, dict):
        base = {}
    sib_paths = sibling_candidates(pack_path)
    sib_objs = [load_json(p) for p in sib_paths]
    view = merged_view(base, sib_objs)

    adapted = {}
    provenance = {}
    # try each expected field via adapter list
    for target, candidates in ADAPTER.items():
        found = None
        from_key = None
        # 1) direct key in base first
        if target in base:
            found = base[target]; from_key = f"{Path(pack_path).name}:{target}"
        # 2) dotted candidates across enriched view
        if found is None:
            for cand in candidates:
                val = deep_get(view, cand) if "." in cand else view.get(cand)
                if val is not None:
                    found = val; from_key = f"(enriched){cand}"
                    break
        adapted[target] = found
        provenance[target] = from_key

    return adapted, provenance, {"sibling_sources": sib_paths}

# ------------------------------
# 8) Report builder
# ------------------------------
def build_verbose(pack_path: str, client_txt: str):
    policies = parse_policy(client_txt)
    adapted, prov, enrich_meta = adapt_to_schema(pack_path)

    report = {
        "pack_id": None,
        "pack_path": pack_path,
        "sibling_sources": enrich_meta["sibling_sources"],
        "policy_snapshot": policies,
        "fields": {},
        "Known_Gaps": []
    }

    # If pack itself has id/track_id try to show it
    base = load_json(pack_path) or {}
    for tid_key in ["track_id","id","meta.id","meta.track_id"]:
        tid = deep_get(base, tid_key) if "." in tid_key else base.get(tid_key)
        if tid:
            report["pack_id"] = tid
            break

    def put(name, value, source):
        info = {
            "raw": value,
            "normalized": normalize_field(name, value),
            "provenance": source,
            "influence_map": FIELD_INFLUENCE.get(name, ["Unknown"])
        }
        # policy-aware status
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

    # flatten MARKET_NORMS.profile
    prof = adapted.get("MARKET_NORMS.profile")
    if prof is not None:
        put("MARKET_NORMS.profile", prof, prov.get("MARKET_NORMS.profile"))
    else:
        report["Known_Gaps"].append("MARKET_NORMS.profile")

    # top-level canonical fields
    for k in ["region","runtime_sec","tempo_bpm","tempo_band_bpm","ttc_sec","exposures"]:
        val = adapted.get(k)
        if val is not None:
            put(k, val, prov.get(k))
        else:
            report["Known_Gaps"].append(k)

    # buckets
    for b in ["sections","hook_positions","rhythm_features","production_features","tonal_features","era_refs","production_tags"]:
        val = adapted.get(b)
        if val is not None:
            put(b, val, prov.get(b))
        else:
            report["Known_Gaps"].append(b)

    report["Known_Gaps"] = sorted(set([g for g in report["Known_Gaps"] if g not in report["fields"]]))
    return report

# ------------------------------
# 9) CLI
# ------------------------------
def main(argv):
    if len(argv) >= 2 and argv[1] == "--policy-only":
        if len(argv) != 3:
            print("Usage: verbose_validator.py --policy-only path/to/client.txt", file=sys.stderr)
            sys.exit(1)
        client_txt = Path(argv[2]).read_text()
        print(json.dumps({"policy_snapshot": parse_policy(client_txt)}, indent=2))
        return

    if len(argv) < 3:
        print("Usage: verbose_validator.py <pack.json> <client.txt>", file=sys.stderr)
        sys.exit(1)

    pack_path, client_path = argv[1], argv[2]
    client_txt = Path(client_path).read_text()
    print(json.dumps(build_verbose(pack_path, client_txt), indent=2))

if __name__ == "__main__":
    main(sys.argv)
