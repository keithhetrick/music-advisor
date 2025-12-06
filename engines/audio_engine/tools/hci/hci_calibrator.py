#!/usr/bin/env python3

# LEGACY: use hci_axes.py + hci_calibration.py instead

import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class Knot:
    x: float
    y: float

def load_knots_from_json(path: str) -> List[Knot]:
    d = json.loads(open(path).read())
    if "knots" in d:
        return [Knot(x=float(k["x"]), y=float(k["y"])) for k in d["knots"]]
    raise KeyError("Expected top-level 'knots' in calibration json")

def fit_affine_for_anchor(raw_values: List[float], target_mean: float) -> Tuple[float, float]:
    """Return (scale, offset) so that mean(scale*x+offset)=target_mean, with gentle centering.
       If variance is tiny, fall back to offset-only shift."""
    if not raw_values:
        return 1.0, 0.0
    m = sum(raw_values)/len(raw_values)
    var = sum((x-m)**2 for x in raw_values)/len(raw_values)
    if var < 1e-6:
        return 1.0, (target_mean - m)
    # keep spread; shift to target mean
    scale = 1.0
    offset = target_mean - m*scale
    return scale, offset

def apply_affine(x: float, scale: float, offset: float, cap_min=0.0, cap_max=1.0) -> float:
    y = scale*x + offset
    if cap_min is not None: y = max(cap_min, y)
    if cap_max is not None: y = min(cap_max, y)
    return y

def calibrate_series(vals: List[float], scale: float, offset: float, cap_min=0.0, cap_max=1.0) -> List[float]:
    return [apply_affine(v, scale, offset, cap_min, cap_max) for v in vals]
