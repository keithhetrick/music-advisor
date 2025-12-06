# aee_ml/models.py
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np

from .config import IDX_TO_BAND

# We keep sklearn imports local to this module so the rest of the repo does not
# depend on it unless you actually run the ML training script.
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
except Exception as exc:  # pragma: no cover - import error path
    sys.stderr.write(
        "[aee_ml.models] ERROR: scikit-learn is required for ML calibration.\n"
        "Install it with: pip install scikit-learn\n"
        f"Underlying error: {exc}\n"
    )
    raise


@dataclass
class AxisReport:
    axis: str
    train_acc: float
    test_acc: float
    n_train: int
    n_test: int
    bands_present: List[str]


def train_axis_model(
    axis: str,
    X: np.ndarray,
    y: np.ndarray,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[LogisticRegression, AxisReport]:
    """Train a multinomial logistic regression for a single 3-band axis.

    Args:
        axis:     name of the axis ("energy" or "dance").
        X:        design matrix, shape (n_samples, n_features).
        y:        encoded labels, shape (n_samples,) with values 0/1/2.
        test_size: fraction for held-out test set (if dataset is big enough).
    """
    uniq = np.unique(y)
    if uniq.shape[0] < 2:
        raise RuntimeError(
            f"Not enough distinct labels for axis '{axis}' (found {uniq.tolist()})"
        )

    stratify = y if uniq.shape[0] > 1 and y.shape[0] >= 10 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size if y.shape[0] >= 5 else 0.0,
        random_state=random_state,
        stratify=stratify,
    )

    model = LogisticRegression(
        multi_class="multinomial",
        max_iter=500,
        C=1.0,
        class_weight="balanced",
        solver="lbfgs",
        n_jobs=None,
    )
    model.fit(X_train, y_train)

    train_acc = float(model.score(X_train, y_train))
    if X_test.shape[0] > 0:
        test_acc = float(model.score(X_test, y_test))
        n_test = int(X_test.shape[0])
    else:
        test_acc = float("nan")
        n_test = 0

    report = AxisReport(
        axis=axis,
        train_acc=train_acc,
        test_acc=test_acc,
        n_train=int(X_train.shape[0]),
        n_test=n_test,
        bands_present=[IDX_TO_BAND[int(b)] for b in uniq],
    )
    return model, report
