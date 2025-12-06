"""
Slice formatters for advisor_host chat replies.
Each formatter returns (parts:list[str], ui_hints:dict, more:bool).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from advisor_host.host.compare import compare_recs

DEFAULT_PHRASING = {
    "friendly": {
        "structure": "Structure highlights:",
        "groove": "Groove/dance highlights:",
        "loudness": "Loudness notes:",
        "mood": "Mood/valence notes:",
        "historical": "Historical echo notes:",
        "optimization": "Ideas to try:",
        "hci": "Score context:",
        "plan": "Plan:",
    },
    "direct": {
        "structure": "Structure:",
        "groove": "Groove:",
        "loudness": "Loudness:",
        "mood": "Mood:",
        "historical": "Historical:",
        "optimization": "Do this next:",
        "hci": "Score:",
        "plan": "Plan:",
    },
    "neutral": {
        "structure": "Structure:",
        "groove": "Groove:",
        "loudness": "Loudness:",
        "mood": "Mood:",
        "historical": "Historical:",
        "optimization": "Next steps:",
        "hci": "Score:",
        "plan": "Plan:",
    },
}


def _phrasing(tone: str, intent: str, profile: Dict[str, Any]) -> str:
    override = (profile.get("phrasing") or {}).get(intent)
    if override:
        return override
    return DEFAULT_PHRASING.get(tone, DEFAULT_PHRASING["neutral"]).get(intent, "")


def _merge_hints(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged = {
        "show_cards": list(set(base.get("show_cards", []) + extra.get("show_cards", []))),
        "quick_actions": base.get("quick_actions", []) + extra.get("quick_actions", []),
        "tone": base.get("tone"),
        "primary_slices": base.get("primary_slices", []),
    }
    if "highlight_axes" in base or "highlight_axes" in extra:
        merged["highlight_axes"] = extra.get("highlight_axes") or base.get("highlight_axes")
    if "_more" in base or "_more" in extra:
        merged["_more"] = extra.get("_more") or base.get("_more")
    return merged


def format_axes(
    intent: str,
    rec: Dict[str, Any],
    profile: Dict[str, Any],
    tone: str,
    offset: int,
    axis_list: List[str],
) -> Tuple[List[str], Dict[str, Any], bool]:
    parts: List[str] = []
    quick_actions: List[Dict[str, str]] = []
    ui: Dict[str, Any] = {"show_cards": ["axes"], "quick_actions": quick_actions, "status": {}}
    axes = rec.get("axes", {}) or {}
    summaries = (rec.get("intent_summaries") or {}).get(intent) or []
    page_size = 3
    slice_axes = axis_list[offset : offset + page_size]
    if summaries:
        parts.extend(summaries[offset : offset + page_size])
    for axis in slice_axes:
        if axis in axes:
            a = axes[axis]
            level = a.get("level")
            mpos = a.get("market_position", "unknown")
            comment = a.get("comment", "")
            parts.append(
                f"{_phrasing(tone, intent, profile)} {axis}: level={level}, market={mpos}. {comment}"
            )
    more = len(axis_list) > offset + page_size
    if summaries and len(summaries) > offset + page_size:
        more = True
    if more:
        parts.append("[more available: say 'more']")
    ui["highlight_axes"] = slice_axes
    quick_actions.append({"label": f"More {intent}", "intent": intent})
    return parts, ui, more


def format_historical(
    rec: Dict[str, Any],
    profile: Dict[str, Any],
    tone: str,
    offset: int,
) -> Tuple[List[str], Dict[str, Any], bool]:
    parts: List[str] = []
    quick_actions: List[Dict[str, str]] = [{"label": "More historical", "intent": "historical"}]
    ui: Dict[str, Any] = {"show_cards": ["historical_echo"], "quick_actions": quick_actions}
    summaries = (rec.get("intent_summaries") or {}).get("historical") or []
    he = rec.get("historical_echo", {}) or {}
    items: List[str] = []
    if summaries:
        items.extend(summaries)
    if he.get("primary_decade_comment"):
        items.append(f"{_phrasing(tone, 'historical', profile)} {he['primary_decade_comment']}")
    if (he.get("top_neighbor") or {}).get("comment"):
        items.append(he["top_neighbor"]["comment"])
    page_size = 3
    slice_items = items[offset : offset + page_size]
    parts.extend(slice_items)
    more = len(items) > offset + page_size
    if more:
        parts.append("[more available: say 'more']")
    return parts, ui, more


def format_opt(
    rec: Dict[str, Any],
    profile: Dict[str, Any],
    tone: str,
    offset: int,
) -> Tuple[List[str], Dict[str, Any], bool]:
    parts: List[str] = []
    quick_actions: List[Dict[str, str]] = [{"label": "More optimizations", "intent": "optimize"}]
    ui: Dict[str, Any] = {"show_cards": ["optimization"], "quick_actions": quick_actions}
    opts = rec.get("optimization") or []
    page_size = 3
    if opts:
        slice_opts = opts[offset : offset + page_size]
        parts.append(_phrasing(tone, "optimization", profile) or "Next steps:")
        parts.extend([f"- {o.get('area')}: {o.get('comment')}" for o in slice_opts])
    more = len(opts) > offset + page_size
    if more:
        parts.append("[more available: say 'more']")
    return parts, ui, more


def format_plan(
    rec: Dict[str, Any],
    profile: Dict[str, Any],
    tone: str,
    offset: int,
) -> Tuple[List[str], Dict[str, Any], bool]:
    parts: List[str] = []
    quick_actions: List[Dict[str, str]] = [{"label": "More plan", "intent": "plan"}]
    ui: Dict[str, Any] = {"show_cards": [], "quick_actions": quick_actions}
    advisor_sections = rec.get("advisor_sections") or {}
    keys = [
        "CURRENT_POSITION",
        "DESTINATION",
        "GAP_MAP",
        "REVERSE_ENGINEERED_ACTIONS",
        "RECOMMENDED_NEXT_MOVES",
        "PHILOSOPHY_REMINDER",
    ]
    items: List[str] = []
    for k in keys:
        section = advisor_sections.get(k) or []
        if section:
            items.append(f"{k}:")
            items.extend(section)
    page_size = 4
    slice_items = items[offset : offset + page_size]
    parts.extend(slice_items)
    more = len(items) > offset + page_size
    if more:
        parts.append("[more available: say 'more']")
    return parts, ui, more


def format_compare(
    rec: Dict[str, Any],
    profile: Dict[str, Any],
    tone: str,
    offset: int,
) -> Tuple[List[str], Dict[str, Any], bool]:
    prev = rec.get("_prev_recommendation") or {}
    lines, changed_axes = compare_recs(prev, rec)
    page_size = 4
    slice_lines = lines[offset : offset + page_size] if lines else []
    more = len(lines) > offset + page_size
    ui: Dict[str, Any] = {
        "show_cards": ["hci"],
        "quick_actions": [{"label": "More compare", "intent": "compare"}],
    }
    if changed_axes:
        ui["highlight_axes"] = changed_axes
        ui["quick_actions"].append({"label": "Show structure", "intent": "structure"})
        ui["quick_actions"].append({"label": "Show groove", "intent": "groove"})
    if more:
        slice_lines.append("[more available: say 'more']")
    # Top deltas card hint
    ui["compare_deltas"] = changed_axes or []
    return slice_lines or ["No prior recommendation to compare against."], ui, more


def format_slice(
    intent: str,
    rec: Dict[str, Any],
    profile: Dict[str, Any],
    tone: str,
    offsets: Dict[str, int],
) -> Tuple[str, Dict[str, Any]]:
    parts: List[str] = []
    ui_hints: Dict[str, Any] = {
        "show_cards": [],
        "quick_actions": [],
        "tone": tone,
        "primary_slices": profile.get("primary_slices", []),
    }
    more = False

    if intent in ("structure", "groove", "loudness", "mood"):
        axis_map = {
            "structure": ["TempoFit", "RuntimeFit"],
            "groove": ["Energy", "Danceability"],
            "loudness": ["LoudnessFit"],
            "mood": ["Valence"],
        }
        p, ui, more = format_axes(intent, rec, profile, tone, offsets.get(intent, 0), axis_map[intent])
        parts.extend(p)
        ui_hints = _merge_hints(ui_hints, ui)
    elif intent == "historical":
        p, ui, more = format_historical(rec, profile, tone, offsets.get(intent, 0))
        parts.extend(p)
        ui_hints = _merge_hints(ui_hints, ui)
    elif intent in ("optimize", "general"):
        p, ui, more = format_opt(rec, profile, tone, offsets.get(intent, 0))
        parts.extend(p)
        ui_hints = _merge_hints(ui_hints, ui)
    elif intent == "plan":
        p, ui, more = format_plan(rec, profile, tone, offsets.get(intent, 0))
        parts.extend(p)
        ui_hints = _merge_hints(ui_hints, ui)
    elif intent == "compare":
        p, ui, _ = format_compare(rec, profile, tone, offsets.get(intent, 0))
        parts.extend(p)
        ui_hints = _merge_hints(ui_hints, ui)
    elif intent == "health":
        # health/status intent (also answers "status")
        meta = rec.get("market_norms_used") or {}
        rec_version = rec.get("rec_version")
        advisor_mode = rec.get("advisor_mode")
        axes = rec.get("axes") or {}
        he = rec.get("historical_echo") or {}
        prov = rec.get("provenance") or {}
        parts.append("Health/status:")
        if meta:
            parts.append("Norms: " + ", ".join([f"{k}={v}" for k, v in meta.items() if v]))
        else:
            parts.append("Norms: none (advisory-only)")
        if rec_version:
            parts.append(f"Rec version: {rec_version}")
        if advisor_mode:
            parts.append(f"Advisor mode: {advisor_mode}")
        if rec.get("advisor_sections"):
            parts.append("Advisor sections available.")
        if prov:
            ns = prov.get("norms_source") or {}
            if ns:
                parts.append(
                    "Provenance: "
                    + ", ".join([f"{k}={v}" for k, v in ns.items() if v])
                )
        parts.append(
            "Data: HCI="
            + ("present" if rec.get("canonical_hci") is not None else "missing")
            + "; axes="
            + ("present" if axes else "missing")
            + "; historical_echo="
            + ("present" if he.get("available") else "missing")
            + "; norms="
            + ("present" if meta else "missing")
            + "."
        )
        if rec.get("warnings"):
            for w in rec.get("warnings", []):
                parts.append(f"Warning: {w}")
        ui_hints["quick_actions"].append({"label": "Show plan", "intent": "plan"})
        ui_hints["quick_actions"].append({"label": "Show commands", "intent": "commands"})
    elif intent == "capabilities":
        parts.append(_phrasing(tone, "capabilities", profile) or "Capabilities:")
        parts.append("- Analyze /audio payloads deterministically (no recompute).")
        parts.append("- Optionally apply market norms if a snapshot is provided.")
        parts.append(
            "- Slice responses by intent: structure/groove/loudness/mood/historical/optimizations/plan/compare."
        )
        parts.append("- Paging via 'more'; quick actions suggest follow-ups.")
        parts.append("- 'plan' shows advisor_sections if provided; 'compare' diffs current vs previous rec.")
        parts.append("- Use 'commands' or 'tutorial' for help; 'health' to see status/norms/rec version.")
        ui_hints["quick_actions"].append({"label": "Show tutorials", "intent": "tutorial"})
    elif intent == "summarize":
        # coarse summary: use hci_comment, axes levels, top 2 optimizations
        parts.append(_phrasing(tone, "summarize", profile) or "Summary:")
        if rec.get("hci_comment"):
            parts.append(rec["hci_comment"])
        axes = rec.get("axes") or {}
        if axes:
            parts.append("Axes: " + ", ".join([f"{k}:{v.get('level')}" for k, v in axes.items()]))
        opts = (rec.get("optimization") or [])[:2]
        if opts:
            parts.append("Key suggestions:")
            parts.extend([f"- {o.get('area')}: {o.get('comment')}" for o in opts])
    elif intent == "expand":
        # fuller expansion: include hci_comment, detailed axes comments, and more optimizations
        parts.append(_phrasing(tone, "expand", profile) or "Details:")
        if rec.get("hci_comment"):
            parts.append(rec["hci_comment"])
        axes = rec.get("axes") or {}
        for axis, val in axes.items():
            parts.append(f"{axis}: {val.get('comment')}")
        opts = (rec.get("optimization") or [])[:5]
        if opts:
            parts.append("Suggestions:")
            parts.extend([f"- {o.get('area')}: {o.get('comment')}" for o in opts])

    if not parts:
        parts.append(rec.get("hci_comment", ""))
        ui_hints["show_cards"].append("hci")

    norms = rec.get("market_norms_used")
    if norms:
        meta_str = ", ".join([f"{k}={v}" for k, v in norms.items() if v])
        parts.append(f"[market_norms] {meta_str}")
    else:
        parts.append("[market_norms] none (advisory-only path)")
    warnings = rec.get("warnings") or []
    if warnings:
        parts.append("Warnings: " + "; ".join(warnings))

    reply = "\n".join([p for p in parts if p])
    if more:
        ui_hints["quick_actions"].append({"label": "More", "intent": intent})
        ui_hints["_more"] = True
    ui_hints["warnings"] = warnings or []
    return reply, ui_hints
