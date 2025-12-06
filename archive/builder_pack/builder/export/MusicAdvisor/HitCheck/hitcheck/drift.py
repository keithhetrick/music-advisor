import numpy as np
from typing import Dict, Any

def zdelta(x: np.ndarray, center: np.ndarray) -> np.ndarray:
    return (x - center)

def drift_summary(x: np.ndarray,
                  cohort_centroid: np.ndarray,
                  neighbor_matrix: np.ndarray,
                  thresholds: Dict[str, float],
                  columns) -> Dict[str, Any]:
    deltas_vs_cohort = zdelta(x, cohort_centroid)
    neigh_center = neighbor_matrix.mean(axis=0) if neighbor_matrix.size else np.zeros_like(x)
    deltas_vs_neigh  = zdelta(x, neigh_center)

    # Build keyed dicts
    vs_cohort = {col: float(val) for col, val in zip(columns, deltas_vs_cohort)}
    vs_neigh  = {col: float(val) for col, val in zip(columns, deltas_vs_neigh)}

    flags = []
    def flag_axis(axis, val):
        thr = thresholds.get(axis, None)
        if thr is not None and abs(val) > thr:
            flags.append({"axis": axis, "z": float(val), "status": "exceeds"})

    for axis, val in vs_cohort.items():
        if axis.endswith("_z") or axis in thresholds:
            flag_axis(axis, val)

    # Rhythm/profile is an embedding distance percentile; handled upstream as 'rhythm_dist' if provided
    return {
        "vs_cohort_centroid": vs_cohort,
        "vs_neighbor_band": vs_neigh,
        "threshold_flags": flags
    }

def drift_penalty(drift_obj: Dict[str, Any], lambda_w: float) -> float:
    # simplistic: proportional to count and average magnitude of exceeded axes (soft cap)
    flags = drift_obj.get("threshold_flags", [])
    if not flags:
        return 0.0
    mags = [abs(f["z"]) for f in flags if "z" in f]
    base = min(0.25, (len(mags) * (sum(mags)/len(mags)) ) / 8.0)
    return float(lambda_w * base)
