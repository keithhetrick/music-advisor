import numpy as np

# ----- robust numeric coercion ------------------------------------------------

def _to_float(x, default=np.nan):
    if x is None:
        return default
    if isinstance(x, str):
        xs = x.strip().lower()
        if xs in ("", "na", "n/a", "null", "none", "nan"):
            return default
    try:
        return float(x)
    except Exception:
        return default

# ----- vector definition (numeric-only) ---------------------------------------

def vector_order():
    # v1.x numeric-only feature vector; categoricals are meta only.
    return [
        "bpm",
        "loudness_lufs",
        "energy",
        "danceability",
        "valence",
        "runtime_sec",
        "ttc_sec",
        "exposures",
    ]

def encode_feature_vector(raw: dict) -> dict:
    """Coerce a raw row (CSV or dict) into normalized fields."""
    out = {}
    # numerics
    out["bpm"]           = _to_float(raw.get("bpm"))
    out["loudness_lufs"] = _to_float(raw.get("loudness_lufs"))
    out["energy"]        = _to_float(raw.get("energy"))
    out["danceability"]  = _to_float(raw.get("danceability"))
    out["valence"]       = _to_float(raw.get("valence"))
    out["runtime_sec"]   = _to_float(raw.get("runtime_sec"))
    out["ttc_sec"]       = _to_float(raw.get("ttc_sec"))
    out["exposures"]     = _to_float(raw.get("exposures"))

    # categoricals (kept for meta, NOT used in numeric vector)
    out["key"]            = (raw.get("key") or "").strip()
    out["mode"]           = (raw.get("mode") or "").strip()
    out["rhythm_profile"] = (raw.get("rhythm_profile") or "").strip()
    out["genre"]          = (raw.get("genre") or "").strip()
    tags = raw.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    out["tags"] = tags if isinstance(tags, list) else []

    # meta passthrough
    out["ref_id"] = raw.get("ref_id", "")
    out["title"]  = raw.get("title", "")
    out["artist"] = raw.get("artist", "")
    return out

def as_vector(feat_dict: dict):
    """Return numpy vector in the defined order, numeric only."""
    return np.array([_to_float(feat_dict.get(k, np.nan)) for k in vector_order()], dtype=float)

def build_norm_stats(X: np.ndarray):
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0)
    sd = np.where(sd == 0, 1.0, sd)
    return {"mean": mu, "std": sd}

def zscore(X: np.ndarray, stats: dict):
    mu, sd = stats["mean"], stats["std"]
    return (X - mu) / sd
