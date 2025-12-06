from __future__ import annotations
import json
from typing import Any, Dict, Optional
from ..commands import hitcheck_commands 

# Lazy import to avoid heavy deps unless called
def _hc(ctx_kwargs: Dict[str, Any]):
    from ...HitCheck.hitcheck.orchestrator import init as hc_init, run as hc_run, export as hc_export
    return hc_init, hc_run, hc_export

# Simple in-memory session store (replace with your session store if you have one)
_SESS: Dict[str, Dict[str, Any]] = {}

def _get_session(sid: str) -> Dict[str, Any]:
    if sid not in _SESS:
        _SESS[sid] = {"ctx": None, "last_result": None}
    return _SESS[sid]

def cmd_hitcheck_init(session_id: str, *, k: int = 8, metric: str = "cosine", alpha: float = 0.12, lambda_: float = 0.08, cfg_path: str = "MusicAdvisor/HitCheck/hitcheck/config.yaml") -> str:
    hc_init, _, _ = _hc({})
    sess = _get_session(session_id)
    sess["ctx"] = hc_init(cfg_path, k=k, metric=metric, alpha=alpha, lambd=lambda_)
    return f"[HitCheck] init: k={k} metric={metric} alpha={alpha} lambda={lambda_}"

def cmd_hitcheck_run(session_id: str, wip_row: Dict[str, Any]) -> str:
    _, hc_run, hc_export = _hc({})
    sess = _get_session(session_id)
    if sess.get("ctx") is None:
        return "[HitCheck] error: not initialized. Run `/hitcheck init …` first."
    result = hc_run(sess["ctx"], wip_row=wip_row)
    sess["last_result"] = result
    # Compact human line
    top = result.get("Top_Cluster", {})
    return f"[HitCheck] run: HCI_v1p={result.get('HCI_v1p'):.3f} · cluster={top.get('name','?')} · resonance={top.get('wip_resonance',0):.3f}"

def cmd_hitcheck_export(session_id: str) -> str:
    _, _, hc_export = _hc({})
    sess = _get_session(session_id)
    if not sess.get("last_result"):
        return "[HitCheck] error: nothing to export. Run `/hitcheck run` first."
    return hc_export(sess["ctx"], sess["last_result"])

# Optional convenience
def cmd_hitcheck_card(session_id: str) -> str:
    sess = _get_session(session_id)
    r = sess.get("last_result")
    if not r: return "[HitCheck] error: nothing to export."
    drift = r["Market_Drift"]
    top = r["Top_Cluster"]
    neighbors = r.get("neighbors", [])[:3]
    lines = [
        "### 🔎 HitCheck Card",
        f"**Params:** k={r['params']['k']}, metric={r['params']['metric']}",
        f"**HCI v1p:** {r['HCI_v1p']:.2f}",
        f"**Top Cluster:** {top.get('name','?')} · wip↔centroid {top.get('wip_resonance',0):.2f}",
        f"**Market Drift (z̄):** {drift['z_magnitude_avg']:.2f}",
        "**Nearest (top 3):**"
    ]
    for i,n in enumerate(neighbors,1):
        lines.append(f"{i}) {n.get('title','?')} — {n.get('artist','?')} · {n.get('rhythm_profile','?')} · sim {n.get('similarity',0):.2f}")
    return "\n".join(lines)

