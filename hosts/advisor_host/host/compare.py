"""
Compare two recommendation objects for user-facing summary.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _diff_axes(prev: Dict[str, Any], curr: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    msgs: List[str] = []
    changed_axes: List[str] = []
    prev_axes = prev.get("axes") or {}
    curr_axes = curr.get("axes") or {}
    for axis, curr_val in curr_axes.items():
        prev_level = (prev_axes.get(axis) or {}).get("level")
        curr_level = curr_val.get("level")
        if prev_level and curr_level and prev_level != curr_level:
            msgs.append(f"{axis}: {prev_level} -> {curr_level}")
            changed_axes.append(axis)
    return msgs, changed_axes


def compare_recs(prev: Dict[str, Any], curr: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    changed_axes: List[str] = []
    if not prev:
        return lines, changed_axes
    prev_hci = prev.get("canonical_hci")
    curr_hci = curr.get("canonical_hci")
    if prev_hci is not None and curr_hci is not None and prev_hci != curr_hci:
        lines.append(f"HCI: {prev_hci} -> {curr_hci} (Δ {curr_hci - prev_hci:+.2f})")
    if prev.get("hci_band") != curr.get("hci_band"):
        lines.append(f"HCI band: {prev.get('hci_band')} -> {curr.get('hci_band')}")
    axes_lines, changed_axes = _diff_axes(prev, curr)
    lines.extend(axes_lines)
    # Optimization deltas (top 2 per rec, area-based)
    prev_opts = {o.get("area"): o for o in (prev.get("optimization") or [])[:2]}
    curr_opts = {o.get("area"): o for o in (curr.get("optimization") or [])[:2]}
    for area, curr_opt in curr_opts.items():
        prev_opt = prev_opts.get(area)
        if prev_opt and prev_opt.get("comment") != curr_opt.get("comment"):
            lines.append(f"Optimization changed ({area}): '{prev_opt.get('comment')}' -> '{curr_opt.get('comment')}'")
    # Norms change
    prev_norms = prev.get("market_norms_used") or {}
    curr_norms = curr.get("market_norms_used") or {}
    if prev_norms != curr_norms and curr_norms:
        lines.append(
            "Norms changed to "
            + ", ".join([f"{k}={v}" for k, v in curr_norms.items() if v])
        )
    return lines, changed_axes
