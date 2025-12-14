"""Shared environment constants for ma_helper.

This centralizes filesystem locations so helpers can import them without
pulling in the entire CLI.
"""
from __future__ import annotations

import os
from pathlib import Path

# Base repo root (ma_helper lives under the repo root as a package)
ROOT = Path(__file__).resolve().parents[2]

# State directory (user overridable)
STATE_HOME = Path(os.environ.get("MA_HELPER_HOME", Path.home() / ".ma_helper"))
# Default cache/state under repo unless overridden; can be replaced by config/no-write
CACHE_DIR = ROOT / ".ma_cache"
CACHE_FILE = CACHE_DIR / "cache.json"
LAST_RESULTS_FILE = CACHE_DIR / "last_results.json"
ARTIFACT_DIR = CACHE_DIR / "artifacts"
LOG_DIR = STATE_HOME / "logs"
LOG_FILE = Path(os.environ.get("MA_LOG_FILE", LOG_DIR / "ma.log"))
TELEMETRY_FILE = Path(os.environ.get("MA_TELEMETRY_FILE", LOG_FILE))
FAVORITES_PATH = STATE_HOME / "config.json"
CACHE_ENABLED = os.environ.get("MA_HELPER_NO_WRITE") != "1"


def apply_config(cfg) -> None:
    """Apply path overrides from HelperConfig; safe no-op if not provided."""
    global CACHE_DIR, CACHE_FILE, LAST_RESULTS_FILE, ARTIFACT_DIR, STATE_HOME, LOG_DIR, LOG_FILE, TELEMETRY_FILE, FAVORITES_PATH, CACHE_ENABLED, ROOT
    if hasattr(cfg, "root") and cfg.root:
        ROOT = cfg.root
    if getattr(cfg, "cache_dir", None):
        CACHE_DIR = cfg.cache_dir
        CACHE_FILE = CACHE_DIR / "cache.json"
        LAST_RESULTS_FILE = CACHE_DIR / "last_results.json"
        ARTIFACT_DIR = CACHE_DIR / "artifacts"
    if getattr(cfg, "state_dir", None):
        STATE_HOME = cfg.state_dir
        LOG_DIR = STATE_HOME / "logs"
        FAVORITES_PATH = STATE_HOME / "config.json"
    if getattr(cfg, "log_file", None):
        LOG_FILE = cfg.log_file
    if getattr(cfg, "telemetry_file", None):
        TELEMETRY_FILE = cfg.telemetry_file
    # MA_LOG_FILE overrides everything
    if os.environ.get("MA_LOG_FILE"):
        LOG_FILE = Path(os.environ["MA_LOG_FILE"])
    if os.environ.get("MA_TELEMETRY_FILE"):
        TELEMETRY_FILE = Path(os.environ["MA_TELEMETRY_FILE"])
    CACHE_ENABLED = os.environ.get("MA_HELPER_NO_WRITE") != "1"
    if not CACHE_ENABLED:
        LOG_FILE = None
        TELEMETRY_FILE = None
