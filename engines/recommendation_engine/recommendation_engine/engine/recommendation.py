from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from recommendation_engine.engine.market_norms import (
    label_percentile,
    percentiles_for_feature,
    validate_norms_snapshot,
)

HCI_EXPERIMENTAL_THRESHOLD = 0.40
HCI_DEVELOPING_THRESHOLD = 0.70
HCI_STRONG_THRESHOLD = 0.90

AXIS_LOW_MAX = 0.39
AXIS_MEDIUM_MAX = 0.69

REC_VERSION = "2025-12-rc1"
REC_BAND_NARRATIVES = {
    "experimental": "Experimental/off-norm; decide whether to lean niche or adjust core axes toward norms.",
    "developing": "Developing/mixed; some axes align, others diverge. Choose lane: niche vs gradual norm alignment.",
    "strong": "Strong alignment; focus on mix clarity, vocals, and transitions rather than big structural changes.",
    "apex": "Apex alignment; keep polish high, avoid over-cooking dynamics, and refine transitions/vocals.",
    "unknown": "No HCI provided; you can still act on axes/norms and historical echo if available.",
}
LYRICS_ADVISORY_NOTE = "Lyrics are advisory-only; no lyric fusion into KPI (40/40 audio/lyric fusion pending LEE graduation)."

AXIS_COMMENT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "TempoFit": {
        "low": "TempoFit is low; tempo sits off typical norms.",
        "medium": "TempoFit is moderate; workable vs norms.",
        "high": "TempoFit is strong; tempo aligns with norms.",
    },
    "RuntimeFit": {
        "low": "RuntimeFit is low; structure length diverges from norms.",
        "medium": "RuntimeFit is moderate.",
        "high": "RuntimeFit is strong; runtime fits norms well.",
    },
    "LoudnessFit": {
        "low": "LoudnessFit is low; loudness differs from modern masters.",
        "medium": "LoudnessFit is workable.",
        "high": "LoudnessFit is strong; loudness matches norms.",
    },
    "Energy": {
        "low": "Energy is restrained; may feel subdued versus norms.",
        "medium": "Energy is balanced.",
        "high": "Energy is strong; matches impactful material.",
    },
    "Danceability": {
        "low": "Danceability is low; groove may feel unstable or niche.",
        "medium": "Danceability is workable.",
        "high": "Danceability is high; groove is body-friendly.",
    },
    "Valence": {
        "low": "Valence is low; mood skews darker.",
        "medium": "Valence is balanced.",
        "high": "Valence is high; bright/positive mood.",
    },
}


def select_canonical_hci(payload: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    if payload.get("HCI_v1_final_score") is not None:
        return float(payload["HCI_v1_final_score"]), "HCI_v1_final_score"
    if payload.get("HCI_v1_score") is not None:
        return float(payload["HCI_v1_score"]), "HCI_v1_score"
    audio_v2 = payload.get("HCI_audio_v2") or {}
    if audio_v2.get("score") is not None:
        return float(audio_v2["score"]), "HCI_audio_v2.score"
    return None, None


def classify_hci_band(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score < HCI_EXPERIMENTAL_THRESHOLD:
        return "experimental"
    if score < HCI_DEVELOPING_THRESHOLD:
        return "developing"
    if score < HCI_STRONG_THRESHOLD:
        return "strong"
    return "apex"


def hci_band_comment(score: Optional[float], band: str) -> str:
    if score is None or band == "unknown":
        return "No canonical HCI score provided; cannot position in bands."
    if band == "experimental":
        return f"HCI ≈ {score:.2f} is experimental/off-norm; audio DNA diverges from typical hit archetypes."
    if band == "developing":
        return f"HCI ≈ {score:.2f} is developing/mixed; some axes align, others diverge."
    if band == "strong":
        return f"HCI ≈ {score:.2f} is strong; good alignment with long-running hit DNA."
    if band == "apex":
        return f"HCI ≈ {score:.2f} is apex; very strong alignment with proven archetypes (not predictive)."
    return "Unrecognized HCI band."


def classify_axis_level(value: Optional[float]) -> str:
    if value is None:
        return "unknown"
    try:
        v = float(value)
    except Exception:
        return "unknown"
    if v <= AXIS_LOW_MAX:
        return "low"
    if v <= AXIS_MEDIUM_MAX:
        return "medium"
    return "high"


def axis_comment(axis_name: str, level: str) -> str:
    tmpl = AXIS_COMMENT_TEMPLATES.get(axis_name)
    if tmpl and level in tmpl:
        return tmpl[level]
    if level == "low":
        return f"{axis_name} is low versus norms."
    if level == "medium":
        return f"{axis_name} is moderate versus norms."
    if level == "high":
        return f"{axis_name} is high versus norms."
    return f"{axis_name} level unknown."


def interpret_axes(audio_axes: Dict[str, Any], norms_snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    interpreted: Dict[str, Dict[str, Any]] = {}
    axes_norms = (norms_snapshot.get("axes") or {}) if norms_snapshot else {}
    for axis_name, raw_value in audio_axes.items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            value = None
        level = classify_axis_level(value)
        comment = axis_comment(axis_name, level)
        norms_stats = axes_norms.get(axis_name) or {}
        interpreted[axis_name] = {
            "value": value,
            "level": level,
            "comment": comment,
            "market_position": label_percentile(value, norms_stats) if norms_stats else "unknown",
        }
    return interpreted


def label_distance(distance: Optional[float]) -> str:
    if distance is None:
        return "unknown"
    try:
        d = float(distance)
    except Exception:
        return "unknown"
    if d <= 0.60:
        return "very close echo"
    if d <= 1.00:
        return "moderately close echo"
    return "looser echo / unique"


def interpret_historical_echo(historical_echo_v1: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not historical_echo_v1:
        return {
            "available": False,
            "summary": "No Tier 1 historical echo neighbors provided.",
            "primary_decade": None,
            "primary_decade_neighbor_count": 0,
            "top_neighbor": None,
        }
    primary_decade = historical_echo_v1.get("primary_decade")
    neighbor_count = historical_echo_v1.get("primary_decade_neighbor_count") or 0
    top_neighbor = historical_echo_v1.get("top_neighbor") or {}
    distance_label = label_distance(top_neighbor.get("distance"))
    if primary_decade:
        decade_comment = f"Primary decade lean: {primary_decade} with ~{neighbor_count} close neighbors."
    else:
        decade_comment = "Primary decade unspecified."
    if top_neighbor:
        tn_artist = top_neighbor.get("artist", "Unknown Artist")
        tn_title = top_neighbor.get("title", "Unknown Title")
        tn_year = top_neighbor.get("year", "Unknown Year")
        neighbor_comment = f"Closest neighbor: {tn_artist} – '{tn_title}' ({tn_year}), {distance_label}."
    else:
        neighbor_comment = "No top neighbor listed."
    return {
        "available": True,
        "primary_decade": primary_decade,
        "primary_decade_neighbor_count": neighbor_count,
        "primary_decade_comment": decade_comment,
        "top_neighbor": {
            "raw": top_neighbor or None,
            "distance_label": distance_label if top_neighbor else None,
            "comment": neighbor_comment,
        },
    }


def compare_features_to_norms(features: Dict[str, Any], norms_snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    comparisons: Dict[str, Dict[str, Any]] = {}
    for key in ("tempo_bpm", "duration_sec", "loudness_LUFS", "energy", "danceability", "valence"):
        stats = percentiles_for_feature(norms_snapshot, key)
        val = features.get(key)
        label = label_percentile(val, stats)
        comparisons[key] = {"value": val, "market_position": label}
    return comparisons


def _add_suggestion(suggestions: List[Dict[str, Any]], area: str, kind: str, comment: str) -> None:
    suggestions.append({"area": area, "kind": kind, "comment": comment})


def generate_intent_summaries(
    axis_interp: Dict[str, Dict[str, Any]],
    feature_positions: Dict[str, Dict[str, Any]],
    historical_echo: Dict[str, Any],
    optimization: List[Dict[str, Any]],
    canonical_hci: Optional[float],
    hci_band: str,
    warnings: List[str],
    features_full: Dict[str, Any],
) -> Dict[str, List[str]]:
    summaries: Dict[str, List[str]] = {}

    def axis_line(names: List[str]) -> List[str]:
        lines: List[str] = []
        for name in names:
            a = axis_interp.get(name) or {}
            level = a.get("level")
            mpos = a.get("market_position", "unknown")
            comment = a.get("comment") or ""
            lines.append(f"{name}: level={level}, market={mpos}. {comment}")
        return lines

    # Structure
    summaries["structure"] = axis_line(["TempoFit", "RuntimeFit"])
    if feature_positions.get("duration_sec"):
        summaries["structure"].append(
            f"Runtime position: {feature_positions['duration_sec'].get('market_position', 'unknown')}."
        )

    # Groove
    summaries["groove"] = axis_line(["Energy", "Danceability"])

    # Loudness
    summaries["loudness"] = axis_line(["LoudnessFit"])
    if feature_positions.get("loudness_LUFS"):
        summaries["loudness"].append(
            f"Loudness position: {feature_positions['loudness_LUFS'].get('market_position', 'unknown')}."
        )

    # Mood
    summaries["mood"] = axis_line(["Valence"])

    # Historical
    if historical_echo.get("available"):
        he_lines: List[str] = []
        if historical_echo.get("primary_decade_comment"):
            he_lines.append(historical_echo["primary_decade_comment"])
        tn = (historical_echo.get("top_neighbor") or {}).get("comment")
        if tn:
            he_lines.append(tn)
        summaries["historical"] = he_lines

    # Strategy
    strat: List[str] = []
    strat.append(REC_BAND_NARRATIVES.get(hci_band, REC_BAND_NARRATIVES["unknown"]))
    # Call out strongest/weakest axes by market position
    axes_sorted = sorted(
        [
            (k, v.get("market_position", "unknown"))
            for k, v in axis_interp.items()
            if v.get("market_position") not in (None, "unknown")
        ],
        key=lambda kv: kv[1],
    )
    if axes_sorted:
        best = axes_sorted[-1]
        worst = axes_sorted[0]
        strat.append(f"Strongest axis: {best[0]} ({best[1]}). Weakest axis: {worst[0]} ({worst[1]}).")
    # Include tempo/runtime/loudness position if present
    if feature_positions:
        tempo_pos = feature_positions.get("tempo_bpm", {}).get("market_position")
        duration_pos = feature_positions.get("duration_sec", {}).get("market_position")
        loud_pos = feature_positions.get("loudness_LUFS", {}).get("market_position")
        bits = []
        if tempo_pos:
            bits.append(f"tempo={tempo_pos}")
        if duration_pos:
            bits.append(f"runtime={duration_pos}")
        if loud_pos:
            bits.append(f"loudness={loud_pos}")
        if bits:
            strat.append("Market positions: " + ", ".join(bits) + ".")
    if warnings:
        strat.extend([f"Warning: {w}" for w in warnings])
    if optimization:
        # highlight top 2 items
        for opt in optimization[:2]:
            strat.append(f"{opt.get('area')}: {opt.get('comment')}")
    summaries["strategy"] = strat

    return summaries


def generate_optimization(
    payload: Dict[str, Any],
    axis_interp: Dict[str, Dict[str, Any]],
    feature_positions: Dict[str, Dict[str, Any]],
    canonical_hci: Optional[float],
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []

    def pos(key: str) -> str:
        return feature_positions.get(key, {}).get("market_position", "unknown")

    # Tempo suggestions
    if pos("tempo_bpm") in ("above_p90", "between_p75_p90"):
        _add_suggestion(
            suggestions,
            "Tempo",
            "market_alignment",
            "Tempo is above typical norms; consider nudging toward common bands if mainstream alignment is desired.",
        )
    elif pos("tempo_bpm") in ("below_p10", "between_p10_p25"):
        _add_suggestion(
            suggestions,
            "Tempo",
            "market_alignment",
            "Tempo is below common norms; a slight lift can improve familiarity if you want mainstream feel.",
        )

    # Runtime suggestions
    if pos("duration_sec") in ("above_p90", "between_p75_p90"):
        _add_suggestion(
            suggestions,
            "Runtime",
            "structure_trim",
            "Runtime is long relative to norms; consider tightening intros/outros or reducing repeats.",
        )
    elif pos("duration_sec") in ("below_p10", "between_p10_p25"):
        _add_suggestion(
            suggestions,
            "Runtime",
            "structure_extend",
            "Runtime is short versus norms; consider adding a fuller verse/bridge for traditional structure.",
        )

    # Loudness suggestions
    if pos("loudness_LUFS") in ("below_p10", "between_p10_p25"):
        _add_suggestion(
            suggestions,
            "Loudness",
            "mix_master",
            "Track is quieter than typical masters; more bus compression/limiting can raise perceived loudness.",
        )
    elif pos("loudness_LUFS") in ("above_p90", "between_p75_p90"):
        _add_suggestion(
            suggestions,
            "Loudness",
            "mix_master",
            "Track is hot versus norms; ease limiting to reduce fatigue while keeping impact.",
        )

    # Groove interactions
    energy = axis_interp.get("Energy", {}).get("level")
    dance = axis_interp.get("Danceability", {}).get("level")
    if energy == "high" and dance == "low":
        _add_suggestion(
            suggestions,
            "Groove",
            "energy_vs_danceability",
            "Energy is high but Danceability is low; simplify drums or tighten kick–bass to stabilize groove.",
        )
    if energy == "low" and dance == "high":
        _add_suggestion(
            suggestions,
            "Energy vs Groove",
            "energy_vs_danceability",
            "Danceability is high but Energy is low; add transient punch or section contrast to lift impact.",
        )

    # Mood suggestions
    val_level = axis_interp.get("Valence", {}).get("level")
    if val_level == "low":
        _add_suggestion(
            suggestions,
            "Valence / Mood",
            "mood_adjust",
            "Mood skews darker; if a brighter feel is desired, use major-leaning harmony or lighter textures in key sections.",
        )
    elif val_level == "high":
        _add_suggestion(
            suggestions,
            "Valence / Mood",
            "mood_balance",
            "Mood is bright; keep some contrast/tension to avoid one-dimensional feel.",
        )

    # HCI strategy suggestion
    if canonical_hci is not None:
        band = classify_hci_band(canonical_hci)
        if band in ("experimental", "developing"):
            _add_suggestion(
                suggestions,
                "Strategy",
                "lane_choice",
                "HCI is experimental/developing; choose whether to lean niche or gently align key axes toward norms.",
            )
        elif band in ("strong", "apex"):
            _add_suggestion(
                suggestions,
                "Strategy",
                "fine_tune",
                "HCI is strong/apex; focus on mix clarity, vocals, and transitions over large structural changes.",
            )
    return suggestions


def compute_recommendation(payload: Dict[str, Any], market_norms_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    norms = validate_norms_snapshot(market_norms_snapshot or {})
    features_full = payload.get("features_full") or {}
    audio_axes = payload.get("audio_axes") or {}
    historical_echo_v1 = payload.get("historical_echo_v1")
    advisor_target = payload.get("advisor_target") or {}
    lane = payload.get("lane") or norms.get("lane") or "advisory"

    canonical_hci, hci_source = select_canonical_hci(payload)
    hci_band = classify_hci_band(canonical_hci)
    hci_comment_text = hci_band_comment(canonical_hci, hci_band)

    axis_interpretation = interpret_axes(audio_axes, norms)
    feature_positions = compare_features_to_norms(features_full, norms)
    historical_echo_summary = interpret_historical_echo(historical_echo_v1)
    optimization_suggestions = generate_optimization(payload, axis_interpretation, feature_positions, canonical_hci)
    warnings: List[str] = []

    intent_summaries = generate_intent_summaries(
        axis_interp=axis_interpretation,
        feature_positions=feature_positions,
        historical_echo=historical_echo_summary,
        optimization=optimization_suggestions,
        canonical_hci=canonical_hci,
        hci_band=hci_band,
        warnings=warnings,
        features_full=features_full,
    )

    recommendation = {
        "rec_version": REC_VERSION,
        "canonical_hci": canonical_hci,
        "canonical_hci_source": hci_source,
        "hci_band": hci_band,
        "hci_comment": hci_comment_text,
        "axes": axis_interpretation,
        "historical_echo": historical_echo_summary,
        "features_vs_market": feature_positions,
        "market_norms_used": {
            "region": norms.get("region"),
            "tier": norms.get("tier"),
            "version": norms.get("version"),
            "last_refreshed_at": norms.get("last_refreshed_at"),
            "lane": norms.get("lane") or lane,
        },
        "optimization": optimization_suggestions,
        "disclaimer": (
            "HCI and these recommendations describe historical echo and norm alignment; they are not hit predictions."
        ),
        "warnings": warnings,
        "advisor_mode": advisor_target.get("mode", "optimize_current"),
        "intent_summaries": intent_summaries,
        "provenance": {
            "rec_version": REC_VERSION,
            "norms_source": {
                "region": norms.get("region"),
                "tier": norms.get("tier"),
                "version": norms.get("version"),
                "lane": norms.get("lane") or lane,
                "last_refreshed_at": norms.get("last_refreshed_at"),
            },
        },
        "lyrics": {
            "status": "advisory_only",
            "note": LYRICS_ADVISORY_NOTE,
        },
    }
    validation: Dict[str, Any] = {"warnings": []}
    if canonical_hci is None:
        msg = "No HCI score found (HCI_v1_final_score, HCI_v1_score, or HCI_audio_v2.score)."
        warnings.append(msg)
        validation["warnings"].append(msg)
    if not audio_axes:
        msg = "audio_axes missing; axis interpretation limited."
        warnings.append(msg)
        validation["warnings"].append(msg)
    if not features_full:
        msg = "features_full missing; market positioning limited."
        warnings.append(msg)
        validation["warnings"].append(msg)
    if validation["warnings"]:
        recommendation["validation"] = validation

    # Optional future_back / structured advisory overlay (textual; non-breaking)
    def build_current_position() -> List[str]:
        lines = []
        lines.append(f"HCI: {canonical_hci if canonical_hci is not None else 'N/A'} ({hci_band})")
        if features_full:
            tempo = features_full.get("tempo_bpm")
            duration = features_full.get("duration_sec")
            loudness = features_full.get("loudness_LUFS")
            lines.append(f"Tempo ~{tempo} BPM; Runtime ~{duration} sec; Loudness ~{loudness} LUFS.")
        if audio_axes:
            axes_summary = ", ".join([f"{k}:{v.get('level')}" for k, v in axis_interpretation.items()])
            lines.append(f"Axes: {axes_summary}")
        if historical_echo_summary.get("available"):
            lines.append(historical_echo_summary.get("primary_decade_comment", ""))
            tn = (historical_echo_summary.get("top_neighbor") or {}).get("comment")
            if tn:
                lines.append(tn)
        return lines

    def build_destination() -> List[str]:
        lines = []
        lane = advisor_target.get("lane")
        if lane:
            lines.append(f"Target lane: {lane}.")
        notes = advisor_target.get("notes")
        if notes:
            lines.append(f"Notes: {notes}")
        constraints = advisor_target.get("constraints") or {}
        if constraints:
            guards = []
            if constraints.get("keep_mood"):
                guards.append("keep mood/valence")
            if constraints.get("keep_tempo_range"):
                guards.append("keep current tempo range")
            if guards:
                lines.append("Constraints: " + ", ".join(guards))
        return lines

    def build_gap_map() -> List[str]:
        lines = []
        axes = axis_interpretation or {}
        good = [k for k, v in axes.items() if v.get("level") == "high"]
        mid = [k for k, v in axes.items() if v.get("level") == "medium"]
        low = [k for k, v in axes.items() if v.get("level") == "low"]
        if good:
            lines.append("Already strong: " + ", ".join(good))
        if mid:
            lines.append("Workable/mixed: " + ", ".join(mid))
        if low:
            lines.append("Largest gaps: " + ", ".join(low))
            low_detail = []
            for name in low:
                a = axes.get(name, {})
                low_detail.append(f"{name} ({a.get('market_position','unknown')})")
            if low_detail:
                lines.append("Gap detail: " + ", ".join(low_detail))
        return lines

    def build_reverse_actions() -> List[str]:
        lines = []
        constraints = advisor_target.get("constraints") or {}
        guards = []
        if constraints.get("keep_mood"):
            guards.append("keep mood/valence steady")
        if constraints.get("keep_tempo_range"):
            guards.append("keep current tempo range")
        if guards:
            lines.append("Guardrails: " + ", ".join(guards))
        # Prioritize low axes first
        low_axes = [k for k, v in axis_interpretation.items() if v.get("level") == "low"]
        for name in low_axes:
            a = axis_interpretation.get(name, {})
            lines.append(f"Raise {name}: {a.get('comment')}")
        # Then include top optimization suggestions
        for opt in (optimization_suggestions or [])[:6]:
            lines.append(f"{opt.get('area')}: {opt.get('comment')}")
        # Add strategy headline
        strat = intent_summaries.get("strategy") or []
        if strat:
            lines.append("Strategy: " + strat[0])
        return lines or ["No specific optimization suggestions generated."]

    if advisor_target.get("mode") == "future_back":
        recommendation["advisor_sections"] = {
            "CURRENT_POSITION": build_current_position(),
            "DESTINATION": build_destination(),
            "GAP_MAP": build_gap_map(),
            "REVERSE_ENGINEERED_ACTIONS": build_reverse_actions(),
            "PHILOSOPHY_REMINDER": [
                "HCI describes historical echo, not a hit prediction. These moves sharpen alignment but do not guarantee outcomes."
            ],
        }
    else:
        recommendation["advisor_sections"] = {
            "CURRENT_POSITION": build_current_position(),
            "RECOMMENDED_NEXT_MOVES": build_reverse_actions(),
            "PHILOSOPHY_REMINDER": [
                "HCI describes historical echo, not a hit prediction. These moves sharpen alignment but do not guarantee outcomes."
            ],
        }
    return recommendation
