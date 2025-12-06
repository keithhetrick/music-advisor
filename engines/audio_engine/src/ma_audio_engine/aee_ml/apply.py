# aee_ml/apply.py
from __future__ import annotations

import json
import math
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .config import (
    AXIS_FEATURE_KEYS,
    BAND_TO_IDX,
    IDX_TO_BAND,
    AEE_ML_VERSION,
)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
    except Exception:
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return float(v)


def load_manifest(model_dir: Path) -> Dict[str, Any]:
    manifest_path = model_dir / "aee_ml_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_models(model_dir: Path) -> tuple[Any, Any]:
    energy_path = model_dir / "axis_energy.pkl"
    dance_path = model_dir / "axis_dance.pkl"

    if not energy_path.is_file() or not dance_path.is_file():
        raise FileNotFoundError(
            f"Expected model files axis_energy.pkl and axis_dance.pkl in {model_dir}"
        )

    with energy_path.open("rb") as f:
        energy_model = pickle.load(f)
    with dance_path.open("rb") as f:
        dance_model = pickle.load(f)

    return energy_model, dance_model


def iter_features_json(root: Path) -> List[Path]:
    if root.is_file() and root.suffix == ".json":
        return [root]
    return sorted(root.rglob("*.features.json"))


def load_features(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_feature_vector(
    feats: Dict[str, Any],
    feature_keys: Sequence[str] | None = None,
) -> np.ndarray:
    keys = feature_keys or AXIS_FEATURE_KEYS
    vec = np.zeros((len(keys),), dtype=float)
    for i, key in enumerate(keys):
        vec[i] = _safe_float(feats.get(key, 0.0), 0.0)
    return vec


def axis_from_model(
    model: Any,
    feature_vec: np.ndarray,
) -> Dict[str, Any]:
    """Return continuous value, band, and per-band probabilities.

    We treat 3 bands as ordinal and map probability mass to a continuous
    axis in 0..1 using an expected-value scheme:

        value = p(lo)*0.2 + p(mid)*0.5 + p(hi)*0.85
    """
    X = feature_vec.reshape(1, -1)

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[0]
        if len(proba) == 3:
            p_lo, p_mid, p_hi = [float(p) for p in proba]
        else:
            p_lo = p_mid = p_hi = 1.0 / 3.0
    else:
        pred_idx = int(model.predict(X)[0])
        p_lo = p_mid = p_hi = 0.0
        if pred_idx == BAND_TO_IDX["lo"]:
            p_lo = 1.0
        elif pred_idx == BAND_TO_IDX["mid"]:
            p_mid = 1.0
        else:
            p_hi = 1.0

    value = p_lo * 0.2 + p_mid * 0.5 + p_hi * 0.85
    band_idx = int(np.argmax([p_lo, p_mid, p_hi]))
    band = IDX_TO_BAND.get(band_idx, "mid")

    return {
        "value": float(max(0.0, min(1.0, value))),
        "band": band,
        "probs": {"lo": p_lo, "mid": p_mid, "hi": p_hi},
    }
