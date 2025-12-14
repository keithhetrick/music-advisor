"""Adapter registry for ma_helper."""
from __future__ import annotations

from typing import Dict

from ma_helper.adapters.orchestrator_ma import get_adapter as ma_adapter
from ma_helper.adapters.mock_adapter import get_adapter as mock_adapter

ADAPTERS: Dict[str, callable] = {
    "ma_orchestrator": ma_adapter,
    "mock": mock_adapter,
}


def get_adapter(name: str):
    fn = ADAPTERS.get(name)
    if not fn:
        raise ValueError(f"Unknown adapter '{name}'")
    return fn
