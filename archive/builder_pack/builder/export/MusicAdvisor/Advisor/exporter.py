# Advisor/exporter.py
from __future__ import annotations
from typing import Dict, Any

# Tolerate both repo-root and legacy shim import paths.
try:
    from Baselines.manager import BaselineManager  # repo-root
except Exception:
    from MusicAdvisor.Baselines.manager import BaselineManager  # legacy shim

from Host.goldilocks import goldilocks_advise


def _resolve_baseline_block() -> Dict[str, Any]:
    """
    Be resilient to different BaselineManager APIs:
    Try several common method/property names; fall back to a minimal stub.
    """
    bm = BaselineManager()
    candidates = (
        "current_baseline_block", "current_block", "current", "get_current", "as_block"
    )

    for name in candidates:
        try:
            attr = getattr(bm, name, None)
            if attr is None:
                continue
            block = attr() if callable(attr) else attr
            if isinstance(block, dict):
                return block
        except Exception:
            # Try the next candidate
            pass

    # Fallback stub if no compatible API is present
    return {
        "id": None,
        "note": "Baseline block unavailable; using safe default for tests.",
        "MARKET_NORMS": {},
    }


def build_advisor_export(hci_payload: Dict[str, Any], ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Assemble final export (HCI + Baseline + optional Goldilocks advisory).
    - Never mutates HCI numbers.
    - Goldilocks is added only if market/emotional summaries exist in ctx.
    """
    ctx = ctx or {}
    baseline_block = _resolve_baseline_block()

    export: Dict[str, Any] = {**hci_payload, "Baseline": baseline_block}

    # Optional: Goldilocks advisory (advisory-only; never changes HCI)
    m = ctx.get("observed_market")
    e = ctx.get("observed_emotional")
    if isinstance(m, (int, float)) and isinstance(e, (int, float)):
        export["Goldilocks"] = goldilocks_advise(
            observed_market=float(m),
            observed_emotional=float(e)
        )

    # Pass through some useful context if present (purely informational)
    if "ttc_gate" in ctx:
        export["TTC_Gate"] = ctx["ttc_gate"]
    if "structural_gates" in ctx:
        export["Structural_Gates"] = ctx["structural_gates"]

    return export
