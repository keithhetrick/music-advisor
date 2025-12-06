# aee_ml/config.py
from __future__ import annotations

from typing import Dict, Tuple

# First ML calibration version for AEE.
AEE_ML_VERSION: str = "aee_ml_v0.1"

# Ordinal encoding for 3-band axes.
BAND_TO_IDX: Dict[str, int] = {"lo": 0, "mid": 1, "hi": 2}
IDX_TO_BAND: Dict[int, str] = {v: k for k, v in BAND_TO_IDX.items()}

# Core numeric feature set drawn from *.features.json
# These are deliberately small and interpretable.
AXIS_FEATURE_KEYS: Tuple[str, ...] = (
    "tempo_bpm",
    "duration_sec",
    "loudness_LUFS",
    "energy",
    "danceability",
    "valence",
)
