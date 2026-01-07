#!/usr/bin/env python
"""
hci_v2_build_training_matrix.py

Join:
  - data/private/local_assets/hci_v2/hci_v2_targets_pop_us_1985_2024.csv  (labels from core_spine)
  - data/private/local_assets/hci_v2/historical_echo_corpus_2025Q4.csv    (100-song audio axes corpus)

to produce:
  - data/private/local_assets/hci_v2/hci_v2_training_pop_us_2025Q4.csv

Each training row contains:
  - slug, year, title, artist
  - six audio axes (TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence)
  - EchoTarget_v2 (supervised target)
  - echo_decile, success_index_raw, etc. for audit

Usage:

  cd ~/music-advisor

  python tools/hci_v2_build_training_matrix.py \
    --targets-csv data/hci_v2_targets_pop_us_1985_2024.csv \
    --corpus-csv  data/historical_echo_corpus_2025Q4.csv \
    --out-csv     data/hci_v2_training_pop_us_2025Q4.csv
"""

import argparse
import csv
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env
from ma_audio_engine.adapters import make_logger
from ma_audio_engine.adapters import utc_now_iso
from ma_audio_engine.adapters.bootstrap import ensure_repo_root
from ma_config.audio import (
    resolve_hci_v2_targets,
    resolve_hci_v2_corpus,
    resolve_hci_v2_training_out,
)
from shared.config.paths import get_hci_v2_corpus_csv, get_hci_v2_targets_csv, get_hci_v2_training_csv

ensure_repo_root()

LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
_log = make_logger("hci_v2_training_matrix", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)


def _warn(msg: str) -> None:
    _log(f"[WARN] {msg}")


def _err(msg: str) -> None:
    _log(f"[ERROR] {msg}")


# ---------- Normalization helpers ----------

def normalize_text(s: Any) -> str:
    """
    Normalize title/artist strings to improve matching:

    - convert to str, lower case
    - strip whitespace
    - remove content in parentheses (...) (e.g. (From "Top Gun"))
    - replace & with 'and'
    - collapse multiple spaces
    """
    if s is None:
        return ""
    txt = str(s).lower().strip()

    # Remove all parenthetical sections
    txt = re.sub(r"\(.*?\)", "", txt)

    # & -> and
    txt = txt.replace("&", "and")

    # Common 'feat.' / 'featuring' noise: just leave them for now; often both
    # sides will either have them or not. We can extend this if needed.

    # Collapse whitespace
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def make_key(year: Any, title: Any, artist: Any) -> Tuple[str, str, str]:
    """
    Canonical key: (year_str, norm_title, norm_artist)
    year_str is just str(year) if not None, otherwise ""
    """
    year_str = ""
    if year is not None and str(year).strip():
        year_str = str(year).strip()
    return (year_str, normalize_text(title), normalize_text(artist))


# ---------- CSV loaders ----------

def load_targets(path: str) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    """
    Load hci_v2_targets CSV (from hci_v2_build_targets.py).

    Expects at least:
      - year
      - title
      - artist
      - EchoTarget_v2

    Also uses:
      - echo_decile
      - success_index_raw
    """
    _log(f"Loading targets from {path}")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    key_to_row: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    missing_label = 0

    for r in rows:
        year = r.get("year")
        title = r.get("title")
        artist = r.get("artist")
        key = make_key(year, title, artist)

        if not r.get("EchoTarget_v2"):
            missing_label += 1
            continue

        if key in key_to_row:
            _warn(f"Duplicate key in targets for {year} — {title} — {artist}; keeping first.")
            continue

        key_to_row[key] = r

    _log(f"Targets: loaded {len(rows)} rows; usable (with label)={len(key_to_row)}, missing_label={missing_label}")
    return key_to_row


def load_corpus(path: str) -> List[Dict[str, Any]]:
    """
    Load historical_echo_corpus_2025Q4.csv.

    Expects columns like:
      - year
      - title
      - artist
      - tempo_fit / TempoFit
      - runtime_fit / RuntimeFit
      - loudness_fit / LoudnessFit
      - energy / Energy
      - danceability / Danceability
      - valence / Valence
    """
    _log(f"Loading corpus from {path}")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    _log(f"Corpus: loaded {len(rows)} rows.")
    return rows


# ---------- Axis / feature extraction ----------

AXIS_SYNONYMS = {
    "TempoFit": ["TempoFit", "tempo_fit", "tempo_fit_norm"],
    "RuntimeFit": ["RuntimeFit", "runtime_fit", "duration_fit", "runtime_fit_norm"],
    "LoudnessFit": ["LoudnessFit", "loudness_fit", "lufs_fit", "loudness_fit_norm"],
    "Energy": ["Energy", "energy"],
    "Danceability": ["Danceability", "danceability"],
    "Valence": ["Valence", "valence"],
}

EXTRA_FEATURE_CANDIDATES = [
    "tempo_bpm",
    "duration_sec",
    "runtime_sec",
    "loudness_LUFS",
    "energy_raw",
    "danceability_raw",
    "valence_raw",
]


def detect_column(fieldnames: List[str], candidates: List[str]) -> Optional[str]:
    """Return the first candidate that exists (case-sensitive) in fieldnames."""
    for c in candidates:
        if c in fieldnames:
            return c
    return None


def build_feature_extractors(fieldnames: List[str]) -> Tuple[Dict[str, str], List[str]]:
    """
    Determine which columns to use as axes and extra features.

    Returns:
      - axis_map: {AxisName -> csv_column_name}
      - extra_features: list of csv_column_names to include if present
    """
    axis_map: Dict[str, str] = {}
    for axis_name, syns in AXIS_SYNONYMS.items():
        col = detect_column(fieldnames, syns)
        if col is not None:
            axis_map[axis_name] = col

    if len(axis_map) < 4:
        _warn(
            f"Only found {len(axis_map)} axis columns out of 6. "
            f"Found: {axis_map}. Training will still proceed but features will be reduced."
        )
    else:
        _log(f"Axis column map: {axis_map}")

    extra_features: List[str] = []
    for c in EXTRA_FEATURE_CANDIDATES:
        if c in fieldnames:
            extra_features.append(c)

    if extra_features:
        _log(f"Extra scalar feature columns found: {extra_features}")
    else:
        _log("No extra scalar feature columns found; training will use axes only.")

    return axis_map, extra_features


# ---------- Training matrix builder ----------

def build_training_matrix(
    targets_csv: str,
    corpus_csv: str,
    out_csv: str,
) -> None:
    # Load data
    targets = load_targets(targets_csv)
    corpus = load_corpus(corpus_csv)

    if not corpus:
        _err("Corpus is empty; aborting.")
        return
    if not targets:
        _err("Targets map is empty; aborting.")
        return

    # Detect features from corpus header
    fieldnames = list(corpus[0].keys())
    axis_map, extra_features = build_feature_extractors(fieldnames)

    # Must have at least some axes
    if not axis_map:
        _err("No recognizable axis columns in corpus CSV; cannot build training matrix.")
        return

    # Join on (year, title, artist)
    rows_out: List[Dict[str, Any]] = []
    matched = 0
    unmatched = 0

    for r in corpus:
        year = r.get("year")
        title = r.get("title")
        artist = r.get("artist")

        key = make_key(year, title, artist)
        t = targets.get(key)
        if t is None:
            unmatched += 1
            continue

        # Build output row
        out: Dict[str, Any] = {}

        # Basic identity
        out["slug"] = r.get("slug") or r.get("audio_name") or ""
        out["year"] = year
        out["title"] = title
        out["artist"] = artist

        # Axes
        for axis_name, col in axis_map.items():
            out[axis_name] = r.get(col)

        # Extra features
        for col in extra_features:
            out[col] = r.get(col)

        # Labels from targets
        out["EchoTarget_v2"] = t.get("EchoTarget_v2")
        out["echo_decile"] = t.get("echo_decile")
        out["success_index_raw"] = t.get("success_index_raw")

        rows_out.append(out)
        matched += 1

    _log(f"Matched {matched} corpus rows to targets; unmatched={unmatched}")

    if not rows_out:
        _err("No joined rows; nothing to write. Check that titles/artists/years line up between CSVs.")
        return

    # Build fieldnames for training CSV (stable order)
    # Identity
    field_order: List[str] = ["slug", "year", "title", "artist"]

    # Axes (in a stable order)
    for axis_name in ["TempoFit", "RuntimeFit", "LoudnessFit", "Energy", "Danceability", "Valence"]:
        if axis_name in rows_out[0]:
            field_order.append(axis_name)

    # Extra features
    for col in extra_features:
        if col not in field_order:
            field_order.append(col)

    # Labels
    for label_col in ["EchoTarget_v2", "echo_decile", "success_index_raw"]:
        if label_col in rows_out[0]:
            field_order.append(label_col)

    _log(f"Writing training matrix to {out_csv} with {len(rows_out)} rows and {len(field_order)} columns.")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_order)
        writer.writeheader()
        for r in rows_out:
            writer.writerow({k: r.get(k) for k in field_order})

    _log("DONE building hci_v2 training matrix.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build HCI_v2 training matrix by joining EchoTarget_v2 labels with 100-song audio corpus."
    )
    parser.add_argument(
        "--targets-csv",
        default=None,
        help=(
            "Path to EchoTarget_v2 labels CSV "
            f"(default honors env HCI_V2_TARGETS_CSV or {get_hci_v2_targets_csv()})"
        ),
    )
    parser.add_argument(
        "--corpus-csv",
        default=None,
        help=(
            "Path to historical echo audio corpus CSV "
            f"(default honors env HCI_V2_CORPUS_CSV or {get_hci_v2_corpus_csv()})"
        ),
    )
    parser.add_argument(
        "--out-csv",
        default=None,
        help=(
            "Output training matrix CSV "
            f"(default honors env HCI_V2_TRAINING_CSV or {get_hci_v2_training_csv()})"
        ),
    )
    parser.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    parser.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(parser)

    args = parser.parse_args()
    apply_log_sandbox_env(args)
    if args.log_redact:
        os.environ["LOG_REDACT"] = "1"
    if args.log_redact_values:
        os.environ["LOG_REDACT_VALUES"] = args.log_redact_values

    resolved_targets = str(resolve_hci_v2_targets(args.targets_csv))
    resolved_corpus = str(resolve_hci_v2_corpus(args.corpus_csv))
    resolved_out = str(resolve_hci_v2_training_out(args.out_csv))

    build_training_matrix(
        targets_csv=resolved_targets,
        corpus_csv=resolved_corpus,
        out_csv=resolved_out,
    )
    _log(f"[DONE] training matrix written to {resolved_out} ts={utc_now_iso()}")


if __name__ == "__main__":
    main()
