# MusicAdvisor/Core/policy.py
import re

def parse_policy(helper_txt: str):
    txt = helper_txt or ""
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
