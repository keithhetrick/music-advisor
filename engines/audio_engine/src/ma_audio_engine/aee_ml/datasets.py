# aee_ml/datasets.py
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .config import AXIS_FEATURE_KEYS, BAND_TO_IDX


@dataclass
class SupervisedRecord:
    """Joined view of benchmark truth + extracted features for one track."""
    audio_name: str
    features: Dict[str, float]
    energy_band: str
    dance_band: str


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
    except Exception:
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return float(v)


def _load_truth_rows(truth_csv: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with truth_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _find_features_json(root: Path, audio_name: str) -> Optional[Path]:
    """Tolerant search for a matching *.features.json file.

    We mirror the general strategy used in ma_benchmark_check.py without
    importing that script, to keep AEE v1.0 frozen.
    """
    candidates: List[Path] = []

    if root.is_file() and root.suffix == ".json":
        candidates = [root]
    else:
        # First pass: stem startswith audio_name
        for p in root.rglob("*.features.json"):
            if p.stem.startswith(audio_name):
                candidates.append(p)

        # Second pass: audio_name appears anywhere in filename
        if not candidates:
            for p in root.rglob("*.features.json"):
                if audio_name in p.name:
                    candidates.append(p)

    if not candidates:
        return None
    if len(candidates) > 1:
        for c in candidates:
            if c.stem == audio_name:
                return c
    return candidates[0]


def _load_features(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_supervised_records(
    truth_csv: Path,
    features_root: Path,
) -> Tuple[List[SupervisedRecord], List[str]]:
    """Join benchmark_truth.csv with *.features.json on audio_name.

    Returns:
        records: list of SupervisedRecord objects used for ML.
        missing_audio_names: list of audio_name entries that had no matching
                             *.features.json file under features_root.
    """
    truth_rows = _load_truth_rows(truth_csv)
    records: List[SupervisedRecord] = []
    missing: List[str] = []

    for row in truth_rows:
        audio_name = (row.get("audio_name") or "").strip()
        if not audio_name:
            continue

        feat_path = _find_features_json(features_root, audio_name)
        if feat_path is None:
            missing.append(audio_name)
            continue

        feats = _load_features(feat_path)

        energy_band = (row.get("energy_band_truth") or "").strip().lower()
        dance_band = (row.get("dance_band_truth") or "").strip().lower()

        if energy_band not in BAND_TO_IDX or dance_band not in BAND_TO_IDX:
            # Skip rows without valid 3-band labels.
            continue

        feat_vec: Dict[str, float] = {}
        for key in AXIS_FEATURE_KEYS:
            feat_vec[key] = _safe_float(feats.get(key, 0.0), 0.0)

        records.append(
            SupervisedRecord(
                audio_name=audio_name,
                features=feat_vec,
                energy_band=energy_band,
                dance_band=dance_band,
            )
        )

    return records, missing


def design_matrix(
    records: Sequence[SupervisedRecord],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert SupervisedRecord list into (X, y_energy, y_dance) matrices.

    X        : shape (n_records, len(AXIS_FEATURE_KEYS))
    y_energy : encoded energy_band_truth (0/1/2)
    y_dance  : encoded dance_band_truth (0/1/2)
    """
    n = len(records)
    d = len(AXIS_FEATURE_KEYS)
    X = np.zeros((n, d), dtype=float)
    y_energy = np.zeros((n,), dtype=int)
    y_dance = np.zeros((n,), dtype=int)

    for i, rec in enumerate(records):
        X[i, :] = [rec.features[k] for k in AXIS_FEATURE_KEYS]
        y_energy[i] = BAND_TO_IDX[rec.energy_band]
        y_dance[i] = BAND_TO_IDX[rec.dance_band]

    return X, y_energy, y_dance
