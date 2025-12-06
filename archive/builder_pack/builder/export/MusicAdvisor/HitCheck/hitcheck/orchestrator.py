import os, json, argparse
import numpy as np

from .normalizer import encode_feature_vector, as_vector, zscore
from .knn import nearest_neighbors
from .projection import hci_v1_projection

# Lazy YAML import to avoid hard import at package time
def _load_cfg(path):
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class HitCheckContext:
    def __init__(self, cfg_path: str):
        self.cfg_path = cfg_path
        self.cfg = _load_cfg(cfg_path)
        self.index = None
        self.defaults = self.cfg.get("defaults", {})

    def load_index(self):
        npz_path = self.cfg["paths"]["index_npz"]
        if not os.path.exists(npz_path):
            raise FileNotFoundError(f"HitCheck index not found: {npz_path}")
        self.index = np.load(npz_path, allow_pickle=True)
        return self.index

    def init_params(self, k=None, metric=None, alpha=None, lambd=None):
        d = self.defaults
        self.k      = int(k if k is not None else d.get("k", 8))
        self.metric = metric if metric is not None else d.get("metric", "cosine")
        self.alpha  = float(alpha if alpha is not None else d.get("alpha", 0.12))
        self.lambd  = float(lambd if lambd is not None else d.get("lambda", 0.08))

def init(cfg_path: str, **kwargs):
    ctx = HitCheckContext(cfg_path)
    ctx.load_index()
    ctx.init_params(**kwargs)
    return ctx

def run(ctx: HitCheckContext, wip_row: dict):
    if ctx.index is None:
        ctx.load_index()

    X_ref = ctx.index["X_ref"]
    mean  = ctx.index["mean"]
    std   = ctx.index["std"]
    meta  = ctx.index["meta"].tolist()
    cohort_hci_mean = float(ctx.index["cohort_hci_mean"])
    columns = ctx.index["columns"].tolist()

    feat = encode_feature_vector(wip_row)
    x = as_vector(feat)
    xz = (x - mean) / std

    idx, sims = nearest_neighbors(xz, X_ref, ctx.k)

    # gather neighbor HCI values
    neighbor_hci = []
    neighbors = []
    for i, s in zip(idx, sims):
        m = meta[int(i)]
        hci = m.get("HCI_v1", None)
        if isinstance(hci, (int, float)):
            neighbor_hci.append(float(hci))
        neighbors.append({
            "ref_id": m.get("ref_id",""),
            "title": m.get("title",""),
            "artist": m.get("artist",""),
            "rhythm_profile": m.get("rhythm_profile",""),
            "similarity": float(s),
        })
    neighbor_hci = np.array(neighbor_hci, dtype=float) if neighbor_hci else np.array([], dtype=float)

    # projection
    hci_v1p = hci_v1_projection(neighbor_hci, sims, cohort_hci_mean, alpha=ctx.alpha, lambd=ctx.lambd)

    # axis drift (z)
    zvals = xz
    drift = {
        "z_magnitude_avg": float(np.linalg.norm(zvals) / np.sqrt(len(zvals))),
        "axis_z": {col: float(val) for col, val in zip(columns, zvals)}
    }

    # cluster proxy: best rhythm_profile among neighbors by mean sim
    cluster_bins = {}
    for n in neighbors:
        rp = n["rhythm_profile"] or "(unknown)"
        cluster_bins.setdefault(rp, []).append(n["similarity"])
    cluster_name, cluster_sim = "(unknown)", 0.0
    for rp, sims_list in cluster_bins.items():
        avg = float(np.mean(sims_list))
        if avg > cluster_sim:
            cluster_name, cluster_sim = rp, avg

    out = {
        "params": {"k": ctx.k, "metric": ctx.metric, "alpha": ctx.alpha, "lambda": ctx.lambd},
        "neighbors": neighbors,
        "HCI_v1p": float(hci_v1p),
        "Market_Drift": drift,
        "Top_Cluster": {"name": cluster_name, "wip_resonance": float(cluster_sim)}
    }
    return out

def export(ctx: HitCheckContext, result: dict):
    return json.dumps(result, ensure_ascii=False, indent=2)
