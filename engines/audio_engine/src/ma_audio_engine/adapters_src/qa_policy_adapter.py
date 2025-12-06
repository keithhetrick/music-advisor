"""
QA policy adapter: thin layer to keep QA threshold selection modular.

Config:
- file: config/qa_policy.json can override named policy thresholds.
- env: none; callers pass policy name/overrides explicitly (CLI/env handled upstream).

Usage:
- `load_qa_policy("strict")` or `load_qa_policy("default", overrides={"silence_ratio": 0.9})`

Notes:
- Overrides are shallow merges; only known fields in QAPolicy are applied.
- Config overrides are optional; unknown keys are ignored to keep behavior stable.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional

from ma_audio_engine.policies.qa_policy import QAPolicy, get_policy

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "qa_policy.json"
_CONFIG_OVERRIDES: Dict[str, Dict[str, float]] = {}

try:
    if _CFG_PATH.exists():
        data = json.loads(_CFG_PATH.read_text())
        if isinstance(data, dict):
            _CONFIG_OVERRIDES = {str(k): v for k, v in data.items() if isinstance(v, dict)}
except Exception:
    # Config overrides are optional; fall back silently.
    _CONFIG_OVERRIDES = {}


def _merge_policy(base: QAPolicy, name: str, overrides: Optional[dict]) -> QAPolicy:
    merged = asdict(base)
    cfg = _CONFIG_OVERRIDES.get(name)
    if cfg:
        for k, v in cfg.items():
            if k in merged:
                merged[k] = v
    if overrides:
        for k, v in overrides.items():
            if k in merged:
                merged[k] = v
    return QAPolicy(**merged)


def load_qa_policy(name: str, overrides: Optional[dict] = None) -> QAPolicy:
    """
    Load a QA policy by name and apply optional overrides (non-destructive).
    This keeps the extractor loosely coupled to the policy implementation and
    allows drop-in config overrides.
    """
    policy = get_policy(name)
    return _merge_policy(policy, name, overrides)
