from typing import List, Dict, Any
from .utils import weighted_mean

def lineage_from_neighbors(neighbor_rows: List[Dict[str, Any]]):
    # similarity-weighted vote over HEM distributions
    acc = {}
    wsum = 0.0
    for row in neighbor_rows:
        w = float(row.get("similarity", 0.0))
        hem = row.get("HEM", {})
        for arch, p in hem.items():
            acc[arch] = acc.get(arch, 0.0) + w * float(p)
        wsum += w
    if wsum <= 1e-9:
        return {"primary": {"archetype":"Unknown","confidence":0.0}}
    # normalize
    for k in list(acc.keys()):
        acc[k] = acc[k] / wsum
    sorted_items = sorted(acc.items(), key=lambda kv: kv[1], reverse=True)
    primary = sorted_items[0] if sorted_items else ("Unknown", 0.0)
    secondary = sorted_items[1] if len(sorted_items)>1 else None
    tertiary = sorted_items[2] if len(sorted_items)>2 else None
    out = {"primary": {"archetype": primary[0], "confidence": round(primary[1], 4)}}
    if secondary: out["secondary"] = {"archetype": secondary[0], "confidence": round(secondary[1],4)}
    if tertiary:  out["tertiary"]  = {"archetype": tertiary[0],  "confidence": round(tertiary[1],4)}
    out["method"] = "kNN-HEM weighted vote"
    return out
