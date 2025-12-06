from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class NormsSnapshot:
    region: str
    tier: str
    version: str
    last_refreshed_at: Optional[str]
    payload: Dict[str, Any]
    path: Path


def load_snapshot(path: Path) -> NormsSnapshot:
    data = json.loads(path.read_text())
    return NormsSnapshot(
        region=data.get("region", ""),
        tier=data.get("tier", ""),
        version=data.get("version", path.stem),
        last_refreshed_at=data.get("last_refreshed_at"),
        payload=data,
        path=path,
    )


def get_market_norms(
    region: str,
    tier: str,
    version: str = "latest",
    root: Path | str = Path("data/market_norms"),
) -> NormsSnapshot:
    """
    File-based retrieval of market norms snapshots.
    - Snapshots should be named like: <region>_<tier>_<version>.json
    - If version == "latest", pick the lexicographically latest matching file.
    """
    root_path = Path(root)
    pattern = f"{region}_{tier}_*.json" if version == "latest" else f"{region}_{tier}_{version}.json"
    matches = sorted(root_path.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No market norms snapshot found for {region}/{tier}/{version} under {root_path}")
    target = matches[-1]
    return load_snapshot(target)
