#!/usr/bin/env python
"""
hci_v2_train_model.py

Train a supervised HCI_audio_v2 model from the axis-based training matrix:

  - Input:  data/private/local_assets/hci_v2/hci_v2_training_pop_us_2025Q4.csv
            (built by hci_v2_build_training_matrix.py)

  - Output: data/private/local_assets/audio_models/audio_hci_v2_model_pop_us_2025Q4.joblib
            data/private/local_assets/audio_models/audio_hci_v2_model_pop_us_2025Q4.meta.json

The target is EchoTarget_v2 (0–1 historical-echo success index).
Features are the six audio axes (TempoFit, RuntimeFit, LoudnessFit, Energy,
Danceability, Valence), plus any extra scalar features that may be present.
"""

import argparse
import csv
import json
import os
from typing import Any, Dict, List, Tuple

import numpy as np
from shared.config.paths import (
    get_audio_hci_v2_model_meta_path,
    get_audio_hci_v2_model_path,
    get_hci_v2_training_csv,
)

try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import train_test_split
except ImportError as e:
    raise SystemExit(
        "scikit-learn is required for hci_v2_train_model.py. "
        "Install it in your venv with:\n\n"
        "  pip install scikit-learn joblib\n"
    ) from e

try:
    import joblib
except ImportError as e:
    raise SystemExit(
        "joblib is required for hci_v2_train_model.py. "
        "Install it in your venv with:\n\n"
        "  pip install joblib\n"
    ) from e


def _log(msg: str) -> None:
    print(f"[INFO] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _err(msg: str) -> None:
    print(f"[ERROR] {msg}")


IDENTITY_COLS = {"slug", "year", "title", "artist"}
LABEL_COL = "EchoTarget_v2"
LABEL_META_COLS = {"echo_decile", "success_index_raw"}


def load_training_csv(path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Load the training matrix CSV and return:
      - rows: list of dicts
      - fieldnames: list of columns
    """
    if not os.path.exists(path):
        _err(f"Training CSV not found: {path}")
        raise SystemExit(1)

    _log(f"Loading training matrix from {path}")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        _err("Training CSV is empty.")
        raise SystemExit(1)

    fieldnames = list(rows[0].keys())
    _log(f"Training CSV has {len(rows)} rows and {len(fieldnames)} columns.")
    return rows, fieldnames


def select_features(fieldnames: List[str]) -> List[str]:
    """
    Choose feature columns: all non-identity, non-label, non-label-meta columns.
    """
    features: List[str] = []
    for c in fieldnames:
        if c in IDENTITY_COLS:
            continue
        if c == LABEL_COL:
            continue
        if c in LABEL_META_COLS:
            continue
        features.append(c)

    if not features:
        _err("No feature columns detected in training CSV.")
        raise SystemExit(1)

    _log(f"Using feature columns: {features}")
    return features


def build_X_y(
    rows: List[Dict[str, Any]],
    feature_cols: List[str],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert rows into NumPy X (features) and y (labels).
    """
    X_list: List[List[float]] = []
    y_list: List[float] = []

    for r in rows:
        label_str = r.get(LABEL_COL)
        if label_str is None or label_str == "":
            continue
        try:
            y_val = float(label_str)
        except ValueError:
            continue

        x_vec: List[float] = []
        for col in feature_cols:
            v = r.get(col)
            if v is None or v == "":
                x_vec.append(0.0)
            else:
                try:
                    x_vec.append(float(v))
                except ValueError:
                    x_vec.append(0.0)

        y_list.append(y_val)
        X_list.append(x_vec)

    if not X_list:
        _err("No usable rows (with numeric EchoTarget_v2) in training data.")
        raise SystemExit(1)

    X = np.array(X_list, dtype=float)
    y = np.array(y_list, dtype=float)

    _log(f"Built X with shape {X.shape}, y with shape {y.shape}.")
    return X, y


def train_model(
    X: np.ndarray,
    y: np.ndarray,
    random_state: int = 42,
) -> Tuple[GradientBoostingRegressor, Dict[str, Any]]:
    """
    Train a GradientBoostingRegressor and compute simple hold-out metrics.
    """
    n_samples = X.shape[0]
    if n_samples < 20:
        _warn(
            f"Training set is small (n={n_samples}). "
            "Model will be noisy; treat HCI_audio_v2 as an experimental overlay."
        )

    # Simple 80/20 split; with small n this is just to sanity-check.
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=random_state,
    )

    # A conservative, shallow boosted regressor
    model = GradientBoostingRegressor(
        loss="squared_error",
        n_estimators=64,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.9,
        random_state=random_state,
    )

    _log("Fitting GradientBoostingRegressor (audio_v2)...")
    model.fit(X_train, y_train)

    # Evaluate on the hold-out set
    y_pred = model.predict(X_val)
    r2 = r2_score(y_val, y_pred)
    mae = mean_absolute_error(y_val, y_pred)

    _log(f"Validation R^2:  {r2:.3f}")
    _log(f"Validation MAE: {mae:.3f}")

    metrics = {
        "val_r2": float(r2),
        "val_mae": float(mae),
        "n_samples": int(n_samples),
        "n_train": int(X_train.shape[0]),
        "n_val": int(X_val.shape[0]),
    }
    return model, metrics


def save_model_and_meta(
    model: GradientBoostingRegressor,
    feature_cols: List[str],
    metrics: Dict[str, Any],
    train_csv: str,
    out_model: str,
    out_meta: str,
) -> None:
    """
    Save the trained model (joblib) and metadata (JSON).
    """
    os.makedirs(os.path.dirname(out_model), exist_ok=True)
    os.makedirs(os.path.dirname(out_meta), exist_ok=True)

    _log(f"Saving model to {out_model}")
    joblib.dump(model, out_model)

    meta = {
        "model_type": "GradientBoostingRegressor",
        "target_label": LABEL_COL,
        "feature_cols": feature_cols,
        "train_csv": train_csv,
        "metrics": metrics,
        "hci_audio_v2_version": "pop_us_2025Q4_v1",
    }

    _log(f"Saving model meta to {out_meta}")
    with open(out_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    _log("DONE training and saving HCI_audio_v2 model.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train HCI_audio_v2 model from axis-based training matrix."
    )
    parser.add_argument(
        "--train-csv",
        default=str(get_hci_v2_training_csv()),
        help=f"Input training matrix CSV (default: {get_hci_v2_training_csv()})",
    )
    parser.add_argument(
        "--out-model",
        default=str(get_audio_hci_v2_model_path()),
        help=f"Output model path (default: {get_audio_hci_v2_model_path()})",
    )
    parser.add_argument(
        "--out-meta",
        default=str(get_audio_hci_v2_model_meta_path()),
        help=f"Output meta JSON path (default: {get_audio_hci_v2_model_meta_path()})",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for train/val split and model (default: 42)",
    )

    args = parser.parse_args()

    rows, fieldnames = load_training_csv(args.train_csv)
    feature_cols = select_features(fieldnames)
    X, y = build_X_y(rows, feature_cols)
    model, metrics = train_model(X, y, random_state=args.random_state)
    save_model_and_meta(
        model=model,
        feature_cols=feature_cols,
        metrics=metrics,
        train_csv=args.train_csv,
        out_model=args.out_model,
        out_meta=args.out_meta,
    )


if __name__ == "__main__":
    main()
