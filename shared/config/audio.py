"""
Audio/HCI config defaults and helpers.

Purpose:
- Centralize HCI/audio profile/config resolution (env/CLI/default precedence) for extractors, injectors, and rankers.
- Expose defaults for calibration/policy/market norms so wrappers and tests can stay data-driven.

Env knobs respected here (override defaults when set):
- AUDIO_HCI_PROFILE / AUDIO_HCI_CALIBRATION
- AUDIO_MARKET_NORMS
- AUDIO_HCI_POLICY
- AUDIO_HCI_V2_CALIBRATION
- HCI_V2_TARGETS_CSV / HCI_V2_CORPUS_CSV / HCI_V2_TRAINING_CSV
- AUDIO_LOUDNESS_NORMS_OUT

All paths are repo-relative by default but honor MA_CALIBRATION_ROOT/MA_DATA_ROOT via path helpers.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from shared.config.paths import (
    get_calibration_root,
    get_hci_v2_corpus_csv,
    get_hci_v2_targets_csv,
    get_hci_v2_training_csv,
)
from shared.config.profiles import resolve_profile_config

# Defaults (paths are repo-relative but honor MA_CALIBRATION_ROOT via get_calibration_root)
DEFAULT_HCI_PROFILE = "hci_pop_us_2025Q4"
DEFAULT_HCI_CALIBRATION_PATH = get_calibration_root() / "hci_calibration_pop_us_2025Q4.json"

DEFAULT_MARKET_NORMS_PATH = get_calibration_root() / "market_norms_us_pop.json"
DEFAULT_AUDIO_POLICY_PATH = get_calibration_root() / "hci_policy_pop_us_audio_v2.json"
DEFAULT_AUDIO_V2_CALIBRATION_PATH = get_calibration_root() / "hci_audio_v2_calibration_pop_us_2025Q4.json"
DEFAULT_HCI_V2_TARGETS_CSV = get_hci_v2_targets_csv()
DEFAULT_HCI_V2_CORPUS_CSV = get_hci_v2_corpus_csv()
DEFAULT_HCI_V2_TRAINING_CSV = get_hci_v2_training_csv()
DEFAULT_LOUDNESS_NORMS_LOCAL_PATH = get_calibration_root() / "loudness_norms_local_v1.json"
DEFAULT_MARKET_NORMS_LOUDNESS_PATH = get_calibration_root() / "market_norms_us_pop_loudness_v1.json"


def load_json_safe(path: Path, log) -> Optional[Dict[str, object]]:
    """Load JSON with warning logs; non-fatal on missing/parse errors."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log(f"[WARN] Config not found: {path}")
    except Exception as exc:  # pragma: no cover - defensive
        log(f"[WARN] Failed to parse JSON config {path}: {exc}")
    return None


def resolve_hci_calibration(
    cli_profile: Optional[str],
    cli_config: Optional[str | Path],
    log=print,
) -> Tuple[str, Path, Optional[Dict[str, object]]]:
    """Resolve HCI calibration profile/config with CLI > env > default precedence."""
    return resolve_profile_config(
        cli_profile=cli_profile,
        cli_config=cli_config,
        env_profile_var="AUDIO_HCI_PROFILE",
        env_config_var="AUDIO_HCI_CALIBRATION",
        default_profile=DEFAULT_HCI_PROFILE,
        default_config_path=DEFAULT_HCI_CALIBRATION_PATH,
        log=log,
    )


def resolve_market_norms(cli_path: Optional[str | Path], log=print) -> Tuple[Path, Optional[Dict[str, object]]]:
    """Resolve market norms JSON path (CLI > env > default) and load it."""
    env_path = os.getenv("AUDIO_MARKET_NORMS")
    path = Path(cli_path).expanduser() if cli_path else (Path(env_path).expanduser() if env_path else DEFAULT_MARKET_NORMS_PATH)
    return path, load_json_safe(path, log)


def resolve_audio_policy(cli_path: Optional[str | Path], log=print) -> Tuple[Path, Optional[Dict[str, object]]]:
    """Resolve audio policy JSON path (CLI > env > default) and load it."""
    env_path = os.getenv("AUDIO_HCI_POLICY")
    path = Path(cli_path).expanduser() if cli_path else (Path(env_path).expanduser() if env_path else DEFAULT_AUDIO_POLICY_PATH)
    return path, load_json_safe(path, log)


def resolve_audio_v2_calibration(cli_path: Optional[str | Path], log=print) -> Tuple[Path, Optional[Dict[str, object]]]:
    """Resolve HCI v2 calibration JSON path (CLI > env > default) and load it."""
    env_path = os.getenv("AUDIO_HCI_V2_CALIBRATION")
    path = Path(cli_path).expanduser() if cli_path else (Path(env_path).expanduser() if env_path else DEFAULT_AUDIO_V2_CALIBRATION_PATH)
    return path, load_json_safe(path, log)


def resolve_hci_v2_targets(cli_path: Optional[str | Path]) -> Path:
    """Resolve HCI v2 targets CSV (CLI > env > default)."""
    env_path = os.getenv("HCI_V2_TARGETS_CSV")
    path = Path(cli_path).expanduser() if cli_path else (Path(env_path).expanduser() if env_path else DEFAULT_HCI_V2_TARGETS_CSV)
    return path


def resolve_hci_v2_corpus(cli_path: Optional[str | Path]) -> Path:
    """Resolve HCI v2 corpus CSV (CLI > env > default)."""
    env_path = os.getenv("HCI_V2_CORPUS_CSV")
    path = Path(cli_path).expanduser() if cli_path else (Path(env_path).expanduser() if env_path else DEFAULT_HCI_V2_CORPUS_CSV)
    return path


def resolve_hci_v2_training_out(cli_path: Optional[str | Path]) -> Path:
    """Resolve HCI v2 training output CSV (CLI > env > default)."""
    env_path = os.getenv("HCI_V2_TRAINING_CSV")
    path = Path(cli_path).expanduser() if cli_path else (Path(env_path).expanduser() if env_path else DEFAULT_HCI_V2_TRAINING_CSV)
    return path


def resolve_loudness_norms_out(cli_path: Optional[str | Path]) -> Path:
    """Resolve loudness norms output JSON path (CLI > env > default)."""
    env_path = os.getenv("AUDIO_LOUDNESS_NORMS_OUT")
    path = Path(cli_path).expanduser() if cli_path else (Path(env_path).expanduser() if env_path else DEFAULT_MARKET_NORMS_LOUDNESS_PATH)
    return path


__all__ = [
    "DEFAULT_HCI_PROFILE",
    "DEFAULT_HCI_CALIBRATION_PATH",
    "DEFAULT_MARKET_NORMS_PATH",
    "DEFAULT_AUDIO_POLICY_PATH",
    "DEFAULT_AUDIO_V2_CALIBRATION_PATH",
    "DEFAULT_HCI_V2_TARGETS_CSV",
    "DEFAULT_HCI_V2_CORPUS_CSV",
    "DEFAULT_HCI_V2_TRAINING_CSV",
    "DEFAULT_LOUDNESS_NORMS_LOCAL_PATH",
    "DEFAULT_MARKET_NORMS_LOUDNESS_PATH",
    "load_json_safe",
    "resolve_hci_calibration",
    "resolve_market_norms",
    "resolve_audio_policy",
    "resolve_audio_v2_calibration",
    "resolve_hci_v2_targets",
    "resolve_hci_v2_corpus",
    "resolve_hci_v2_training_out",
    "resolve_loudness_norms_out",
]
