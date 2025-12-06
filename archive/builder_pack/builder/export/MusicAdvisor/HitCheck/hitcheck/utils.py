import json, os, math
from typing import Any, Dict

_CACHE: Dict[str, Any] = {}

def cache_set(key: str, value: Any) -> None:
    _CACHE[key] = value

def cache_get(key: str, default=None):
    return _CACHE.get(key, default)

def clamp(x: float, lo: float, hi: float) -> float:
    if x < lo: return lo
    if x > hi: return hi
    return x

def weighted_mean(values, weights):
    s_w = sum(weights) + 1e-12
    return sum(v*w for v, w in zip(values, weights)) / s_w

def safe_stdev(values):
    n = len(values)
    if n < 2: return 0.0
    m = sum(values)/n
    var = sum((v-m)**2 for v in values) / (n-1)
    return math.sqrt(var)

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
