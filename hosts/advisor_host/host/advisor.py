"""
Deterministic advisory host logic.

- Treats incoming payload values as ground truth (no recompute).
- Selects canonical HCI score with fixed priority.
- Interprets audio axes and historical echo.
- Emits structured advisory dict usable by any UI/GPT/macOS host.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from recommendation_engine.engine.recommendation import compute_recommendation as _compute_recommendation
except Exception:  # noqa: BLE001
    _compute_recommendation = None

HCI_EXPERIMENTAL_THRESHOLD = 0.40
HCI_DEVELOPING_THRESHOLD = 0.70
HCI_STRONG_THRESHOLD = 0.90

AXIS_LOW_MAX = 0.39
AXIS_MEDIUM_MAX = 0.69

HCI_DISCLAIMER = (
    "HCI describes historical echo in the audio (alignment with long-running US Pop norms); "
    "it is not a hit predictor and ignores marketing, artist status, or release timing. "
    "The host does not alter or recompute numeric scores."
)

AXIS_COMMENT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "TempoFit": {
        "low": (
            "Tempo sits outside typical hit norms; this can feel niche. "
            "A small BPM nudge toward common bands in your lane can increase familiarity."
        ),
        "medium": "Tempo is reasonably aligned with historical norms.",
        "high": "Tempo strongly matches established hit norms, aiding accessible pacing.",
    },
    "RuntimeFit": {
        "low": (
            "Runtime is atypical versus single/playlist norms. "
            "Tighten intros/outros or trims if you want more radio/playlist utility."
        ),
        "medium": "Runtime is close to historical averages; structure should feel natural.",
        "high": "Runtime fits proven single-length norms, helping usability.",
    },
    "LoudnessFit": {
        "low": (
            "Loudness is off-norm versus modern masters (either too quiet or overly pushed). "
            "Adjust bus compression/limiting to balance competitiveness and dynamics."
        ),
        "medium": "Loudness is workable for modern material.",
        "high": "Loudness closely matches modern master norms, aiding playlist consistency.",
    },
    "Energy": {
        "low": "Energy is restrained; can feel intimate but subdued in pop contexts.",
        "medium": "Energy feels balanced and engaging.",
        "high": "Energy is strong and forward; supports impactful sections.",
    },
    "Danceability": {
        "low": "Groove is less body-oriented; rhythms may feel freeform or busy.",
        "medium": "Groove is workable; listeners can move to it without being club-focused.",
        "high": "Groove is body-friendly and pattern-locked; strong for playlists.",
    },
    "Valence": {
        "low": "Mood skews darker/introspective.",
        "medium": "Valence is balanced; flexible emotional placement.",
        "high": "Tone is bright/positive; aligns with feel-good spaces.",
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
        return (
            "No canonical HCI score was provided. Axes and features can still be interpreted, "
            "but the track cannot be placed in an HCI band."
        )
    if band == "experimental":
        return (
            f"HCI ≈ {score:.2f} sits in an experimental/off-norm band; audio DNA diverges from "
            "typical US Pop archetypes."
        )
    if band == "developing":
        return (
            f"HCI ≈ {score:.2f} is developing/mixed; some axes align while others diverge."
        )
    if band == "strong":
        return (
            f"HCI ≈ {score:.2f} is in a strong historical-echo band; good alignment with long-running hit DNA."
        )
    if band == "apex":
        return (
            f"HCI ≈ {score:.2f} is in an apex echo band; very strong alignment with "
            "proven archetypes (not a guarantee of success)."
        )
    return "Unrecognized HCI band."


def classify_axis_level(value: Optional[float]) -> str:
    if value is None:
        return "unknown"
    if value <= AXIS_LOW_MAX:
        return "low"
    if value <= AXIS_MEDIUM_MAX:
        return "medium"
    return "high"


def axis_comment(axis_name: str, level: str) -> str:
    axis_templates = AXIS_COMMENT_TEMPLATES.get(axis_name)
    if axis_templates and level in axis_templates:
        return axis_templates[level]
    if level == "low":
        return f"{axis_name} is low relative to hit norms."
    if level == "medium":
        return f"{axis_name} is moderate/acceptable versus norms."
    if level == "high":
        return f"{axis_name} is strongly aligned with norms."
    return f"{axis_name} level is unknown."


def interpret_axes(audio_axes: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    interpreted: Dict[str, Dict[str, Any]] = {}
    for axis_name, raw_value in audio_axes.items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            value = None
        level = classify_axis_level(value)
        comment = axis_comment(axis_name, level)
        interpreted[axis_name] = {"value": value, "level": level, "comment": comment}
    return interpreted


def label_distance(distance: Optional[float]) -> str:
    if distance is None:
        return "unknown"
    if distance <= 0.60:
        return "very close echo"
    if distance <= 1.00:
        return "moderately close echo"
    return "looser echo / unique"


def interpret_historical_echo(historical_echo_v1: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not historical_echo_v1:
        return {
            "available": False,
            "summary": "No Tier 1 historical echo neighbors provided; using core features only.",
            "primary_decade": None,
            "primary_decade_neighbor_count": 0,
            "top_neighbor": None,
        }
    primary_decade = historical_echo_v1.get("primary_decade")
    neighbor_count = historical_echo_v1.get("primary_decade_neighbor_count") or 0
    top_neighbor = historical_echo_v1.get("top_neighbor") or {}
    distance_label = label_distance(top_neighbor.get("distance"))

    if primary_decade:
        decade_comment = (
            f"Primary decade lean: {primary_decade} with ~{neighbor_count} close neighbors."
        )
    else:
        decade_comment = "Primary decade is unspecified."

    if top_neighbor:
        tn_artist = top_neighbor.get("artist", "Unknown Artist")
        tn_title = top_neighbor.get("title", "Unknown Title")
        tn_year = top_neighbor.get("year", "Unknown Year")
        neighbor_comment = (
            f"Closest neighbor: {tn_artist} – '{tn_title}' ({tn_year}), {distance_label}."
        )
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


def generate_optimization_suggestions(
    payload: Dict[str, Any],
    axis_interpretation: Dict[str, Dict[str, Any]],
    canonical_hci: Optional[float],
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    features = payload.get("features_full") or {}

    duration_sec = features.get("duration_sec")
    loudness_lufs = features.get("loudness_LUFS")

    tempo_fit = axis_interpretation.get("TempoFit", {})
    runtime_fit = axis_interpretation.get("RuntimeFit", {})
    loudness_fit = axis_interpretation.get("LoudnessFit", {})
    energy = axis_interpretation.get("Energy", {})
    danceability = axis_interpretation.get("Danceability", {})
    valence = axis_interpretation.get("Valence", {})

    if tempo_fit.get("level") == "low":
        suggestions.append(
            {
                "area": "TempoFit",
                "comment": (
                    "TempoFit is low. Consider small BPM nudges toward common bands in your genre "
                    "(e.g., ~85–105 or ~115–130 for pop) if you want more mainstream feel."
                ),
            }
        )

    if runtime_fit.get("level") == "low" and isinstance(duration_sec, (int, float)):
        if duration_sec > 270:
            msg = (
                "RuntimeFit is low and duration is long. Tighten intros/outros or reduce repeats "
                "to land nearer ~2:30–3:30."
            )
        elif duration_sec < 120:
            msg = (
                "RuntimeFit is low and duration is very short. Consider adding a fuller second "
                "verse/chorus or bridge."
            )
        else:
            msg = (
                "RuntimeFit is low. Review intro length, breakdowns, and repeats to rebalance flow."
            )
        suggestions.append({"area": "Runtime", "comment": msg})

    if loudness_fit.get("level") == "low" and isinstance(loudness_lufs, (int, float)):
        suggestions.append(
            {
                "area": "Loudness",
                "comment": (
                    "LoudnessFit is low. If quieter than peers, consider more bus compression/limiting; "
                    "if overly hot, ease limiting to reduce fatigue."
                ),
            }
        )

    if energy.get("level") == "high" and danceability.get("level") == "low":
        suggestions.append(
            {
                "area": "Groove",
                "comment": (
                    "Energy is high while Danceability is low. Simplify drum patterns or tighten "
                    "kick/bass lock to stabilize groove."
                ),
            }
        )

    if energy.get("level") == "low" and danceability.get("level") == "high":
        suggestions.append(
            {
                "area": "Energy vs Groove",
                "comment": (
                    "Danceability is high but Energy is low. Add transient punch or section "
                    "contrast to lift impact without changing BPM."
                ),
            }
        )

    if valence.get("level") == "low":
        suggestions.append(
            {
                "area": "Valence / Mood",
                "comment": (
                    "Valence is low (darker). If a brighter feel is desired, use more "
                    "major-leaning harmony or lighter textures in key sections."
                ),
            }
        )
    elif valence.get("level") == "high":
        suggestions.append(
            {
                "area": "Valence / Mood",
                "comment": (
                    "Valence is high (bright). Maintain some contrast/tension to avoid one-dimensional feel."
                ),
            }
        )

    if canonical_hci is not None:
        band = classify_hci_band(canonical_hci)
        if band in ("experimental", "developing"):
            suggestions.append(
                {
                    "area": "Strategy",
                    "comment": (
                        "HCI band is experimental/developing. Decide whether to lean into "
                        "uniqueness or gently align axes (tempo/runtime/loudness/groove) toward "
                        "common archetypes."
                    ),
                }
            )
        elif band in ("strong", "apex"):
            suggestions.append(
                {
                    "area": "Strategy",
                    "comment": (
                        "HCI band is strong/apex. Focus on mix clarity, vocal presence, transitions, and "
                        "emotion rather than major structural changes."
                    ),
                }
            )
    return suggestions


def run_advisory(payload: Dict[str, Any]) -> Dict[str, Any]:
    warnings: List[str] = []

    features_full = payload.get("features_full")
    audio_axes = payload.get("audio_axes") or {}
    historical_echo_v1 = payload.get("historical_echo_v1")

    if features_full is None:
        warnings.append("features_full missing; tempo/runtime/loudness guidance is limited.")
    if not audio_axes:
        warnings.append("audio_axes missing; axis interpretation empty.")

    canonical_hci, hci_source = select_canonical_hci(payload)
    if canonical_hci is None:
        warnings.append(
            "No HCI score found (HCI_v1_final_score, HCI_v1_score, or HCI_audio_v2.score). "
            "Cannot place track in HCI band."
        )

    hci_band = classify_hci_band(canonical_hci)
    hci_comment_text = hci_band_comment(canonical_hci, hci_band)

    axis_interpretation = interpret_axes(audio_axes)
    historical_echo_summary = interpret_historical_echo(historical_echo_v1)
    optimization_suggestions = generate_optimization_suggestions(
        payload=payload, axis_interpretation=axis_interpretation, canonical_hci=canonical_hci
    )

    return {
        "rec_version": "advisory-local",
        "advisor_mode": "optimize_current",
        "canonical_hci": canonical_hci,
        "canonical_hci_source": hci_source,
        "hci_band": hci_band,
        "hci_comment": hci_comment_text,
        "axes": axis_interpretation,
        "historical_echo": historical_echo_summary,
        "optimization": optimization_suggestions,
        "market_norms_used": {},
        "intent_summaries": {},
        "provenance": {
            "rec_version": "advisory-local",
            "norms_source": None,
        },
        "validation": {"warnings": warnings.copy()},
        "disclaimer": HCI_DISCLAIMER,
        "warnings": warnings,
    }


def run_recommendation(payload: Dict[str, Any], market_norms_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preferred path: norm-aware recommendation if available; otherwise fallback to advisory-only.
    """
    if _compute_recommendation is None:
        advisory = run_advisory(payload)
        advisory["warnings"].append("recommendation_engine not available; fell back to advisory-only output.")
        return advisory
    return _compute_recommendation(payload, market_norms_snapshot)
