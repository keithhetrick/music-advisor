# aee_ml/__init__.py
"""
AEE_ML: Lightweight ML calibration layer for the Audio Echo Engine (AEE).

This package is intentionally small and self-contained so it can be lifted into
a future Audio Intelligence Engine (AIE) repo with minimal changes.

Contents:
    - config.py   : band encodings, feature keys, version constants.
    - datasets.py : join benchmark_truth.csv + *.features.json → X, y.
    - models.py   : training helpers (logistic regression, AxisReport).
    - apply.py    : apply trained models to features → ML axis outputs.

The public API is small and designed for CLI wrappers in tools/ to consume.
"""

from .config import (
    AEE_ML_VERSION,
    AXIS_FEATURE_KEYS,
    BAND_TO_IDX,
    IDX_TO_BAND,
)

from .datasets import (
    SupervisedRecord,
    build_supervised_records,
    design_matrix,
)

from .models import (
    AxisReport,
    train_axis_model,
)

from .apply import (
    axis_from_model,
    make_feature_vector,
    iter_features_json,
    load_features,
    load_manifest,
    load_models,
)
