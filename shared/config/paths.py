"""
Repo-wide path helpers with env overrides.

Env overrides:
- MA_DATA_ROOT: base data directory (default: ./data).
- MA_CALIBRATION_ROOT: base calibration directory (default: ./calibration).
- MA_EXTERNAL_DATA_ROOT: base directory for external datasets (default: <MA_DATA_ROOT>/external).
- MA_KAGGLE_YEAR_END_LYRICS: override for the Kaggle Year-End lyrics CSV.
- MA_HOT100_LYRICS_AUDIO: override for the Hot 100 lyrics+audio CSV.
- MA_CORE1600_CSV: override for the Core1600 CSV path.

Side effects: none; pure path resolution helpers (expanduser on env paths). Keep
callers using these instead of hard-coded paths to preserve portability across
monorepo moves and env overrides.
"""
from __future__ import annotations

import os
from pathlib import Path

# Base roots (overridable via env)
MA_DATA_ROOT = Path(os.getenv("MA_DATA_ROOT", "data")).resolve()
DATA_PUBLIC_ROOT = MA_DATA_ROOT / "public"
DATA_PRIVATE_ROOT = MA_DATA_ROOT / "private"
FEATURES_OUTPUT_ROOT = MA_DATA_ROOT / "features_output"

# Private/local asset roots (non-S3, local-only)
def get_private_root(data_root: Path | None = None) -> Path:
    """Base private data directory (default: <data>/private)."""
    return (data_root or get_data_root()) / "private"


def get_local_assets_root(data_root: Path | None = None) -> Path:
    """Local assets bucket under private/ (default: <data>/private/local_assets)."""
    return get_private_root(data_root) / "local_assets"


def get_hci_v2_root(data_root: Path | None = None) -> Path:
    """Local HCI v2 corpus/targets/training files."""
    return get_local_assets_root(data_root) / "hci_v2"


def get_core_spine_root(data_root: Path | None = None) -> Path:
    """Local core spine CSVs (seed, patched, overrides)."""
    return get_local_assets_root(data_root) / "core_spine"


def get_yearend_hot100_root(data_root: Path | None = None) -> Path:
    """Local Year-End Hot 100 aggregates."""
    return get_local_assets_root(data_root) / "yearend_hot100"


def get_audio_models_root(data_root: Path | None = None) -> Path:
    """Local trained model artifacts (joblib/meta)."""
    return get_local_assets_root(data_root) / "audio_models"


def _env_path(name: str, default: Path) -> Path:
    """Return a Path from an env override if set, else the provided default."""
    val = os.getenv(name)
    return Path(val).expanduser() if val else default


def get_repo_root() -> Path:
    """Resolve the repo root (two+ levels above this file). Used by pipeline/adapters for absolute paths."""
    return Path(__file__).resolve().parents[2]


def get_data_root() -> Path:
    """Base data directory (env MA_DATA_ROOT, default <repo>/data)."""
    return _env_path("MA_DATA_ROOT", get_repo_root() / "data")


def get_calibration_root() -> Path:
    """Base calibration directory (env MA_CALIBRATION_ROOT, default <repo>/shared/calibration)."""
    return _env_path("MA_CALIBRATION_ROOT", get_repo_root() / "shared" / "calibration")


def get_external_data_root(data_root: Path | None = None) -> Path:
    """External datasets root (env MA_EXTERNAL_DATA_ROOT, default <data_root>/private/local_assets/external)."""
    root = get_local_assets_root(data_root)
    return _env_path("MA_EXTERNAL_DATA_ROOT", root / "external")


def get_lyric_intel_db_path(data_root: Path | None = None) -> Path:
    """
    Lyric Intel SQLite DB path.

    Default: <data_root>/private/local_assets/lyric_intel/lyric_intel.db
    If MA_LYRIC_INTEL_DB is set, use that.
    """
    env_path = os.getenv("MA_LYRIC_INTEL_DB")
    if env_path:
        return Path(env_path).expanduser()
    root = get_local_assets_root(data_root)
    return root / "lyric_intel" / "lyric_intel.db"


def get_historical_echo_db_path(data_root: Path | None = None) -> Path:
    """Historical Echo SQLite DB path (default <data_root>/private/local_assets/historical_echo/historical_echo.db)."""
    root = get_local_assets_root(data_root)
    return root / "historical_echo" / "historical_echo.db"


def get_features_output_root(data_root: Path | None = None) -> Path:
    """Root folder for pipeline outputs (default <data_root>/features_output)."""
    root = data_root or get_data_root()
    return root / "features_output"


def get_kaggle_year_end_lyrics_path(data_root: Path | None = None) -> Path:
    """Kaggle Year-End lyrics CSV path (env MA_KAGGLE_YEAR_END_LYRICS)."""
    default = get_external_data_root(data_root) / "year_end" / "year_end_hot_100_lyrics_kaylin_1965_2015.csv"
    return _env_path("MA_KAGGLE_YEAR_END_LYRICS", default)


def get_hot100_lyrics_audio_path(data_root: Path | None = None) -> Path:
    """Hot 100 lyrics+audio CSV path (env MA_HOT100_LYRICS_AUDIO)."""
    default = get_external_data_root(data_root) / "lyrics" / "hot_100_lyrics_audio_2000_2023.csv"
    return _env_path("MA_HOT100_LYRICS_AUDIO", default)


def get_core_1600_csv_path(data_root: Path | None = None) -> Path:
    """Core1600 CSV path (env MA_CORE1600_CSV)."""
    default = get_core_spine_root(data_root) / "core_1600_with_spotify_patched.csv"
    return _env_path("MA_CORE1600_CSV", default)


def get_hci_v2_targets_csv(data_root: Path | None = None) -> Path:
    """EchoTarget v2 labels CSV."""
    return get_hci_v2_root(data_root) / "hci_v2_targets_pop_us_1985_2024.csv"


def get_hci_v2_corpus_csv(data_root: Path | None = None) -> Path:
    """Historical Echo corpus CSV."""
    return get_hci_v2_root(data_root) / "historical_echo_corpus_2025Q4.csv"


def get_hci_v2_training_csv(data_root: Path | None = None) -> Path:
    """HCI v2 training matrix CSV."""
    return get_hci_v2_root(data_root) / "hci_v2_training_pop_us_2025Q4.csv"


def get_hci_v2_training_eval_csv(data_root: Path | None = None) -> Path:
    """HCI v2 training eval CSV."""
    return get_hci_v2_root(data_root) / "hci_v2_training_eval_pop_us_2025Q4.csv"


def get_hci_v2_overlap_csv(data_root: Path | None = None) -> Path:
    """HCI v2 overlap/diagnostics CSV."""
    return get_hci_v2_root(data_root) / "hci_v2_overlap_audio_vs_spine.csv"


def get_hci_v2_audio_seed_csv(data_root: Path | None = None) -> Path:
    """HCI v2 audio selection seed CSV."""
    return get_hci_v2_root(data_root) / "hci_v2_audio_selection_seed.csv"


def get_audio_hci_v2_model_path(data_root: Path | None = None) -> Path:
    """Trained HCI v2 audio model artifact."""
    return get_audio_models_root(data_root) / "audio_hci_v2_model_pop_us_2025Q4.joblib"


def get_audio_hci_v2_model_meta_path(data_root: Path | None = None) -> Path:
    """Trained HCI v2 audio model meta JSON."""
    return get_audio_models_root(data_root) / "audio_hci_v2_model_pop_us_2025Q4.meta.json"


def get_audio_hci_v2_calibration_path(data_root: Path | None = None) -> Path:
    """Calibration index JSON for HCI v2 audio."""
    return get_audio_models_root(data_root) / "audio_hci_v2_calibration_pop_us_2025Q4.json"


def get_yearend_hot100_top100_path(data_root: Path | None = None) -> Path:
    """Year-End Hot 100 Top 100 CSV path."""
    return get_yearend_hot100_root(data_root) / "yearend_hot100_top100_1985_2024.csv"


def get_yearend_hot100_top200_path(data_root: Path | None = None) -> Path:
    """Year-End Hot 100 Top 200 CSV path."""
    return get_yearend_hot100_root(data_root) / "yearend_hot100_top200_1985_2024.csv"


def get_spine_root(data_root: Path | None = None) -> Path:
    """Base folder for spine datasets (env MA_SPINE_ROOT, default <data>/public/spine)."""
    root = data_root or get_data_root()
    return _env_path("MA_SPINE_ROOT", root / "public" / "spine")


def get_spine_backfill_root(data_root: Path | None = None) -> Path:
    """Backfill output root (env MA_SPINE_BACKFILL_ROOT, default <data>/spine/backfill)."""
    base = get_spine_root(data_root)
    return _env_path("MA_SPINE_BACKFILL_ROOT", base / "backfill")


def get_spine_master_csv(data_root: Path | None = None) -> Path:
    """Master spine CSV (env MA_SPINE_MASTER, default <data>/public/spine/spine_master.csv)."""
    root = data_root or get_data_root()
    default = root / "public" / "spine" / "spine_master.csv"
    return _env_path("MA_SPINE_MASTER", default)


def market_norms_path(data_root: Path | None = None) -> Path:
    """Market norms JSON path (default <data>/public/market_norms/market_norms_us_pop.json)."""
    root = data_root or get_data_root()
    default = root / "public" / "market_norms" / "market_norms_us_pop.json"
    return _env_path("MA_MARKET_NORMS_PATH", default)
