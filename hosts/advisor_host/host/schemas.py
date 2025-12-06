"""
Lightweight typing helpers for host payloads/advisories.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict


class AdvisorTarget(TypedDict, total=False):
    mode: str
    lane: str
    constraints: Dict[str, Any]
    notes: str


class HistoricalEcho(TypedDict, total=False):
    primary_decade: Optional[str]
    primary_decade_neighbor_count: int
    top_neighbor: Dict[str, Any]
    neighbors: list


class Advisory(TypedDict, total=False):
    canonical_hci: Optional[float]
    canonical_hci_source: Optional[str]
    hci_band: str
    hci_comment: str
    axes: Dict[str, Dict[str, Any]]
    historical_echo: Dict[str, Any]
    optimization: list
    disclaimer: str
    warnings: list
