#!/usr/bin/env python3
from statistics import mean

def fit_affine_for_anchor(raw_values, target_mean):
    """
    Keep spread (scale=1.0) and shift mean to target.
    If no variance or empty, return identity/offset-only safely.
    """
    if not raw_values:
        return 1.0, 0.0
    m = mean(raw_values)
    return 1.0, (target_mean - m)
