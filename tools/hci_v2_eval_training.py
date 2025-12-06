#!/usr/bin/env python
"""
hci_v2_eval_training.py

Diagnostics helper for HCI_audio_v2:

- Loads the training matrix used for HCI_audio_v2 (EchoTarget_v2) regression.
- Loads the trained model + meta (feature_cols, metrics).
- Recomputes predictions for *all* training rows.
- Outputs a CSV with per-track:
    slug, year, title, artist,
    EchoTarget_v2 (label),
    HCI_audio_v2_hat (prediction),
    residual, abs_residual,
    and the feature columns.

This lets you see how well the model tracks the historical-echo target
for each benchmark anchor.
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
    get_hci_v2_training_eval_csv,
)

try:
    import joblib
except ImportError as e:
    raise SystemExit(
        "joblib is required for hci_v2_eval_training.py. "
        "Install it in your venv with:\n\n"
        "  pip install joblib\n"
    ) from e

LABEL_COL = "EchoTarget_v2"
IDENTITY_COLS = ["slug", "year", "title", "artist"]


def _log(msg: str) -> None:
    print(f"[INFO] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _err(msg: str) -> None:
    print(f"[ERROR] {msg}")


def load_training_csv(path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
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


def load_model_and_meta(model_path: str, meta_path: str):
    if not os.path.exists(model_path):
        _err(f"Model file not found: {model_path}")
        raise SystemExit(1)
    if not os.path.exists(meta_path):
        _err(f"Meta JSON not found: {meta_path}")
        raise SystemExit(1)

    _log(f"Loading model from {model_path}")
    model = joblib.load(model_path)

    _log(f"Loading meta from {meta_path}")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    feature_cols = meta.get("feature_cols")
    if not feature_cols:
        _err("Meta JSON missing 'feature_cols'; cannot evaluate.")
        raise SystemExit(1)

    return model, meta, feature_cols


def build_X_y(
    rows: List[Dict[str, Any]],
    feature_cols: List[str],
) -> Tuple[np.ndarray, np.ndarray, List[int]]:
    """
    Build X (features) and y (labels) from training rows.

    Returns:
      X: shape (n_samples, n_features)
      y: shape (n_samples,)
      idx_kept: indices of rows that had usable labels
    """
    X_list: List[List[float]] = []
    y_list: List[float] = []
    idx_kept: List[int] = []

    for i, r in enumerate(rows):
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

        X_list.append(x_vec)
        y_list.append(y_val)
        idx_kept.append(i)

    if not X_list:
        _err("No usable rows (with numeric EchoTarget_v2) to evaluate.")
        raise SystemExit(1)

    X = np.array(X_list, dtype=float)
    y = np.array(y_list, dtype=float)

    _log(f"Built X with shape {X.shape}, y with shape {y.shape} for evaluation.")
    return X, y, idx_kept


def evaluate(
    model,
    X: np.ndarray,
    y: np.ndarray,
) -> Dict[str, float]:
    y_hat = model.predict(X)
    y_hat = np.array(y_hat, dtype=float)

    # Clamp to [0, 1] for consistency
    y_hat = np.clip(y_hat, 0.0, 1.0)

    residuals = y_hat - y
    abs_residuals = np.abs(residuals)

    mae = float(abs_residuals.mean())
    mse = float((residuals ** 2).mean())
    # simple R^2 on training set
    ss_tot = float(((y - y.mean()) ** 2).sum())
    ss_res = float((residuals ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    _log(f"Training-set MAE: {mae:.4f}")
    _log(f"Training-set MSE: {mse:.4f}")
    _log(f"Training-set R^2: {r2:.4f}")

    return {
        "mae": mae,
        "mse": mse,
        "r2": r2,
        "n_samples": int(len(y)),
    }, y_hat, residuals, abs_residuals


def write_eval_csv(
    out_path: str,
    rows: List[Dict[str, Any]],
    idx_kept: List[int],
    feature_cols: List[str],
    y: np.ndarray,
    y_hat: np.ndarray,
    residuals: np.ndarray,
    abs_residuals: np.ndarray,
) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    fieldnames: List[str] = []
    fieldnames.extend(IDENTITY_COLS)
    fieldnames.append(LABEL_COL)
    fieldnames.append("HCI_audio_v2_hat")
    fieldnames.append("residual")
    fieldnames.append("abs_residual")
    fieldnames.extend(feature_cols)

    # Sort by abs_residual descending (worst fit at top)
    order = np.argsort(-abs_residuals)

    _log(f"Writing training eval CSV to {out_path}")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx in order:
            row_idx = idx_kept[idx]
            base = rows[row_idx]

            out_row: Dict[str, Any] = {}

            for col in IDENTITY_COLS:
                out_row[col] = base.get(col)

            out_row[LABEL_COL] = f"{y[idx]:.6f}"
            out_row["HCI_audio_v2_hat"] = f"{y_hat[idx]:.6f}"
            out_row["residual"] = f"{residuals[idx]:.6f}"
            out_row["abs_residual"] = f"{abs_residuals[idx]:.6f}"

            for col in feature_cols:
                out_row[col] = base.get(col)

            writer.writerow(out_row)

    _log("DONE writing eval CSV.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate HCI_audio_v2 model against training matrix and write per-track diagnostics."
    )
    parser.add_argument(
        "--train-csv",
        default=str(get_hci_v2_training_csv()),
        help=f"Training matrix CSV (default: {get_hci_v2_training_csv()})",
    )
    parser.add_argument(
        "--model",
        default=str(get_audio_hci_v2_model_path()),
        help=f"Trained model path (default: {get_audio_hci_v2_model_path()})",
    )
    parser.add_argument(
        "--meta",
        default=str(get_audio_hci_v2_model_meta_path()),
        help=f"Meta JSON path (default: {get_audio_hci_v2_model_meta_path()})",
    )
    parser.add_argument(
        "--out",
        default=str(get_hci_v2_training_eval_csv()),
        help=f"Output CSV with per-track eval (default: {get_hci_v2_training_eval_csv()})",
    )

    args = parser.parse_args()

    rows, _ = load_training_csv(args.train_csv)
    model, meta, feature_cols = load_model_and_meta(args.model, args.meta)
    _log(f"Using feature_cols from meta: {feature_cols}")

    X, y, idx_kept = build_X_y(rows, feature_cols)
    metrics, y_hat, residuals, abs_residuals = evaluate(model, X, y)

    _log(
        "Summary metrics (training-set): "
        f"MAE={metrics['mae']:.4f}, MSE={metrics['mse']:.4f}, R2={metrics['r2']:.4f}, "
        f"n_samples={metrics['n_samples']}"
    )

    write_eval_csv(
        out_path=args.out,
        rows=rows,
        idx_kept=idx_kept,
        feature_cols=feature_cols,
        y=y,
        y_hat=y_hat,
        residuals=residuals,
        abs_residuals=abs_residuals,
    )


if __name__ == "__main__":
    main()
