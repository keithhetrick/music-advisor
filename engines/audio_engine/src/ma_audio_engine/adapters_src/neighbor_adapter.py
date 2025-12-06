"""
Neighbor adapter: serialize neighbor sets with schema and size guards.

Guards:
- Ensures neighbors is a list of dicts with year/artist/title/distance.
- Truncates to max_neighbors if provided.
- Soft size cap via max_bytes (JSON length); falls back to top 50 if oversized.

Usage:
- `write_neighbors_file(path, payload, max_neighbors=200, max_bytes=200000, warnings=warns, debug=log)`

Notes:
- Side effects: writes JSON to disk; mutates the provided `warnings` list in-place if supplied.
- Payload is shallow-copied before mutation to avoid modifying caller data.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, List, Callable


def write_neighbors_file(
    path: str,
    payload: Dict[str, Any],
    max_neighbors: Optional[int] = None,
    max_bytes: Optional[int] = None,
    warnings: Optional[List[str]] = None,
    debug: Optional[Callable[[str], None]] = None,
) -> None:
    dbg = debug or (lambda _msg: None)
    warn_list = warnings if warnings is not None else []
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = payload.copy()
    neigh = data.get("neighbors")
    if neigh is None:
        warn_list.append("neighbors_missing_list")
        neigh = []
    if neigh is not None and not isinstance(neigh, list):
        neigh = []
    if max_neighbors is not None and isinstance(neigh, list):
        neigh = neigh[:max_neighbors]
    # schema guard: keep only entries with the core fields
    if isinstance(neigh, list):
        clean_neigh = []
        for n in neigh:
            if not isinstance(n, dict):
                continue
            if not {"year", "artist", "title", "distance"} <= set(n.keys()):
                continue
            clean_neigh.append(n)
        if len(clean_neigh) < (len(neigh) if neigh else 0):
            warn_list.append("neighbors_filtered_invalid")
        neigh = clean_neigh
    if neigh is not None:
        data["neighbors"] = neigh
    if max_bytes is not None:
        # soft guard; truncate neighbors if serialized size would exceed cap
        serialized = json.dumps(data, ensure_ascii=False)
        if len(serialized.encode("utf-8")) > max_bytes and isinstance(neigh, list):
            # keep only top 50 as a last resort
            data["neighbors"] = neigh[: min(len(neigh), 50)]
            warn_list.append("neighbors_truncated_for_size")
            dbg("neighbor_adapter: truncated neighbors to fit size cap")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
