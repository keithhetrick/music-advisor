# MusicAdvisor/Dashboard/validate.py
import json
import argparse
from pathlib import Path

# local imports from the engine package
from MusicAdvisor.Core.ingest_pipeline import ingest
try:
    # if you already have a policy parser, import it; else inline a tiny one
    from MusicAdvisor.Core.policy import parse_policy  # optional
except Exception:
    import re
    def parse_policy(txt: str):
        sp = {
            "mode": ("strict" if "mode=strict" in txt.lower()
                     else ("optional" if "mode=optional" in txt.lower() else None)),
            "reliable": "reliable=true" in txt.lower(),
            "use_ttc": "use_ttc=true" in txt.lower(),
            "use_exposures": "use_exposures=true" in txt.lower(),
        }
        pri_m = re.search(r"priors\s*=\s*\{([^}]+)\}", txt, re.IGNORECASE)
        cap_m = re.search(r"caps\s*=\s*\{([^}]+)\}", txt, re.IGNORECASE)
        gp = {
            "active": "GOLDILOCKS_POLICY: active=true" in txt,
            "priors_raw": pri_m.group(1) if pri_m else None,
            "caps_raw": cap_m.group(1) if cap_m else None
        }
        return {"STRUCTURE_POLICY": sp, "GOLDILOCKS_POLICY": gp}

def main():
    p = argparse.ArgumentParser(description="Field Utilization Map (dashboard validate)")
    p.add_argument("--pack", required=True, help="Path to pack JSON")
    p.add_argument("--client", required=True, help="Path to client.txt (policies)")
    p.add_argument("--json", action="store_true", help="Print raw JSON only")
    args = p.parse_args()

    gpt_txt = Path(args.client).read_text(encoding="utf-8", errors="ignore")
    staged = ingest(args.pack, gpt_txt)  # builds MVP + Buckets + Audit

    used = [k for k,v in staged["MVP"].items() if v is not None]
    gaps = [k for k,v in staged["MVP"].items() if v is None]
    payload = {
        "policy_snapshot": parse_policy(gpt_txt),
        "used": used,
        "Known_Gaps": gaps,
        "Buckets": list(staged["Buckets"].keys()),
        "Audit": staged["Audit"]
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("=== Policy Snapshot ===")
        print(json.dumps(payload["policy_snapshot"], indent=2))
        print("\n=== Used MVP Fields ===")
        print(", ".join(used) if used else "(none)")
        print("\n=== Known Gaps (MVP) ===")
        print(", ".join(gaps) if gaps else "(none)")
        print("\n=== Buckets Present ===")
        print(", ".join(payload["Buckets"]) if payload["Buckets"] else "(none)")
        print("\n=== Provenance (where values came from) ===")
        print(json.dumps(payload["Audit"], indent=2))

if __name__ == "__main__":
    main()
