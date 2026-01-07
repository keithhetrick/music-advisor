#!/usr/bin/env python3
from __future__ import annotations

"""
hci_final_score.py

Compute (or annotate) HCI_v1_final_score for .hci.json files, with role-aware
logic for benchmark vs WIP, and attach clear, human-readable tier labels.

Key design points:

- By default, we DO NOT change existing HCI_v1_final_score values.
  If a file already has HCI_v1_final_score and --recompute is NOT set,
  we preserve the numeric score and only refresh:
    * HCI_v1_final_tier
    * HCI_v1_metric_kind
    * HCI_v1_is_hit_predictor
    * HCI_v1_interpretation
    * HCI_v1_notes
    * HCI_v1_debug (source annotations)

- If a file does NOT have HCI_v1_final_score yet OR --recompute is passed,
  we compute a new final score from:
    * HCI_audio_v2.score (preferred)
    * HCI_v1_score      (fallback)
    * HCI_v1_score_raw  (last-ditch fallback)

- Benchmarks:
    final_score ≈ calibrated audio score (clamped [0,1]).

- WIPs:
    final_score is a shrunk / capped version of the base score:
      base ≈ HCI_audio_v2.score (or HCI_v1_score)
      final = wip_anchor + wip_alpha * (base - wip_anchor), clamped [0, wip_cap]

  Defaults (matching current behavior):
    wip_anchor = 0.65
    wip_alpha  = 0.66
    wip_cap    = 0.90

- Tier naming for benchmarks:
    S, A, B, C

- Tier naming for WIPs (historical-echo-centric):
    >= 0.85:  WIP-A+ — Very strong hit draft (historical-echo audio)
    0.75–0.85: WIP-A  — Strong, hit-leaning draft (historical-echo audio)
    0.65–0.75: WIP-B  — Competitive draft (historical-echo audio)
    < 0.65:    WIP-C  — Early draft / needs work (historical-echo audio)

Additionally, we embed explicit metadata on every .hci.json:

    "HCI_v1_metric_kind": "historical_echo_audio",
    "HCI_v1_is_hit_predictor": false,
    "HCI_v1_interpretation": "Historical-echo-centric audio metric ... NOT a hit predictor",
    "HCI_v1_notes": "Sanity check: a WIP copy of 'Blinding Lights' ..."

This makes the core philosophy unmissable in any human-facing surface
  that reads these fields (client packs, UI, documentation).
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env
from ma_audio_engine.adapters import make_logger
from ma_audio_engine.adapters import utc_now_iso
from ma_audio_engine.adapters import load_log_settings


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _extract_base_score(hci: Dict[str, Any]) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    Try to recover a 'base' audio score from the .hci.json.

    Priority:
      1) HCI_audio_v2.score
      2) HCI_v1_score
      3) HCI_v1_score_raw

    Returns (base_score, debug_info)
    """
    debug: Dict[str, Any] = {}

    base = None

    audio_v2 = hci.get("HCI_audio_v2")
    if isinstance(audio_v2, dict):
        score = audio_v2.get("score")
        if isinstance(score, (int, float)):
            base = float(score)
            debug["base_source"] = "HCI_audio_v2.score"

    if base is None:
        v1_score = hci.get("HCI_v1_score")
        if isinstance(v1_score, (int, float)):
            base = float(v1_score)
            debug["base_source"] = "HCI_v1_score"

    if base is None:
        v1_raw = hci.get("HCI_v1_score_raw")
        if isinstance(v1_raw, (int, float)):
            base = float(v1_raw)
            debug["base_source"] = "HCI_v1_score_raw"

    if base is not None:
        debug["base_value"] = base
    else:
        debug["base_source"] = "none"

    return base, debug


def _compute_final_score(
    hci: Dict[str, Any],
    role: str,
    wip_anchor: float,
    wip_alpha: float,
    wip_cap: float,
    recompute: bool,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    Decide what HCI_v1_final_score should be.

    If recompute=False and HCI_v1_final_score already exists, we keep it.
    Otherwise we compute a role-aware final score from the base audio score.
    """
    debug: Dict[str, Any] = {}

    existing = hci.get("HCI_v1_final_score")
    if existing is not None and not recompute:
        try:
            final = float(existing)
            debug["final_source"] = "existing"
            debug["final_existing"] = final
            return final, debug
        except Exception:
            # If it's malformed, fall through to recompute.
            debug["final_source"] = "existing_malformed_recompute"

    # Need to compute a new final score.
    base, base_debug = _extract_base_score(hci)
    debug.update(base_debug)

    if base is None:
        debug["final_source"] = "none"
        return None, debug

    if role == "benchmark":
        # Benchmarks: take calibrated audio score more or less directly.
        final = _clamp01(base)
        debug["final_source"] = "benchmark_from_base"
    else:
        # WIP: shrink toward anchor and cap.
        anchor = float(wip_anchor)
        alpha = float(wip_alpha)
        cap = float(wip_cap)

        # Simple linear shrinkage around anchor.
        final = anchor + alpha * (base - anchor)
        final = _clamp01(final)
        if final > cap:
            final = cap
            debug["final_capped"] = True
        else:
            debug["final_capped"] = False

        debug["final_source"] = "wip_from_base"
        debug["wip_anchor"] = anchor
        debug["wip_alpha"] = alpha
        debug["wip_cap"] = cap

    debug["final_value"] = final
    return final, debug


def _assign_tier(final_score: float, role: str) -> str:
    """
    Map a numeric final_score and role to a human-readable tier label.
    This is where we make the 'too generous' concern more conservative,
    especially in the WIP naming.

    IMPORTANT:
      - These names are explicitly historical-echo-centric.
      - They do NOT promise or imply future commercial success.
    """
    if role == "benchmark":
        # Benchmarks: S / A / B / C
        if final_score >= 0.92:
            return "S — Elite / Benchmark"
        if final_score >= 0.84:
            return "A — Strong / Hit-ready"
        if final_score >= 0.72:
            return "B — Solid / Above-market"
        return "C — Below benchmark band"

    # WIP roles: historical-echo-centric tiers
    if final_score >= 0.85:
        return "WIP-A+ — Very strong hit draft (historical-echo audio)"
    if final_score >= 0.75:
        return "WIP-A — Strong, hit-leaning draft (historical-echo audio)"
    if final_score >= 0.65:
        return "WIP-B — Competitive draft (historical-echo audio)"
    return "WIP-C — Early draft / needs work (historical-echo audio)"


def _attach_metric_metadata(hci: Dict[str, Any]) -> None:
    """
    Stamp explicit metadata on the .hci.json so that any human-facing surface
(client packs, UI, docs) can see the philosophy clearly.
    """
    metric_kind = "historical_echo_audio"
    is_hit_predictor = False
    interpretation = (
        "Historical-echo-centric audio metric. Measures how this audio file’s "
        "features align with long-running US Pop hit archetypes; it does NOT "
        "predict commercial success, streams, virality, or cultural impact. "
        "It is a diagnostic tool for audio shape and historical echo, not a "
        "hit-prediction oracle."
    )
    notes = (
        "Sanity check example: a WIP copy of 'Blinding Lights' is kept in the "
        "WIP folder as a trap/check and currently scores around 0.66 on this "
        "metric, even though the real song is the most-streamed track of all "
        "time. This is expected. The score reflects only the audio file’s "
        "historical-echo profile (tempo, loudness, runtime, energy, "
        "danceability, valence, etc.), not its real-world success, marketing, "
        "or cultural footprint."
    )

    hci["HCI_v1_metric_kind"] = metric_kind
    hci["HCI_v1_is_hit_predictor"] = is_hit_predictor
    hci["HCI_v1_interpretation"] = interpretation
    hci["HCI_v1_notes"] = notes


def apply_final_score(
    hci: Dict[str, Any],
    *,
    wip_anchor: float = 0.65,
    wip_alpha: float = 0.66,
    wip_cap: float = 0.90,
    recompute: bool = False,
) -> Dict[str, Any]:
    """
    Pure helper: returns updated HCI dict with final score/tier/metadata applied.
    """
    hci = dict(hci)
    base_score, debug = _extract_base_score(hci)
    existing_final = hci.get("HCI_v1_final_score")

    final_score = existing_final if existing_final is not None else base_score
    role = str(hci.get("HCI_v1_role") or "unknown")

    if recompute or final_score is None:
        final_score, _ = _compute_final_score(
            hci=hci,
            role=role,
            wip_anchor=wip_anchor,
            wip_alpha=wip_alpha,
            wip_cap=wip_cap,
            recompute=True,
        )
    else:
        debug["base_source"] = debug.get("base_source") or "existing_final_score"

    hci["HCI_v1_final_score"] = final_score
    hci["HCI_v1_final_tier"] = _assign_tier(final_score, role)
    hci["HCI_v1_metric_kind"] = "historical_echo_audio"
    hci["HCI_v1_is_hit_predictor"] = False
    _attach_metric_metadata(hci)

    hci.setdefault("HCI_v1_debug", {})
    hci["HCI_v1_debug"]["final_score"] = final_score
    hci["HCI_v1_debug"]["base_source"] = debug.get("base_source")
    hci["HCI_v1_debug"]["recompute"] = bool(recompute)
    return hci


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Apply final-score policy to .hci.json files, with separate "
            "behavior for benchmark vs WIP, and attach explicit historical-echo "
            "metadata (not a hit predictor)."
        )
    )
    ap.add_argument(
        "--root",
        action="append",
        required=True,
        help="Root directory to scan for *.hci.json (can be given multiple times).",
    )
    ap.add_argument(
        "--wip-anchor",
        type=float,
        default=0.65,
        help="Anchor value for WIP shrinkage (default: 0.65).",
    )
    ap.add_argument(
        "--wip-alpha",
        type=float,
        default=0.66,
        help="Shrinkage factor for WIP scores toward anchor (default: 0.66).",
    )
    ap.add_argument(
        "--wip-cap",
        type=float,
        default=0.90,
        help="Hard cap on WIP final scores (default: 0.90).",
    )
    ap.add_argument(
        "--recompute",
        action="store_true",
        help=(
            "If set, recompute HCI_v1_final_score from base scores even if it already "
            "exists. By default, we preserve existing final scores and only refresh "
            "tiers + metadata."
        ),
    )
    ap.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    ap.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(ap)

    args = ap.parse_args()

    apply_log_sandbox_env(args)
    log_settings = load_log_settings(args)
    redact_flag = log_settings.log_redact or args.log_redact
    redact_values = log_settings.log_redact_values or [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
    log = make_logger("hci_final_score", redact=redact_flag, secrets=redact_values)

    log(
        f"[INFO] Applying final-score policy under roots: "
        f"{', '.join(str(Path(r).resolve()) for r in args.root)}"
    )
    log(
        f"[INFO] Policy: wip_anchor={args.wip_anchor}, "
        f"wip_alpha={args.wip_alpha}, wip_cap={args.wip_cap}, "
        f"recompute={args.recompute}"
    )

    updated = 0
    skipped = 0

    for root_str in args.root:
        root = Path(root_str).expanduser().resolve()
        if not root.exists():
            log(f"[WARN] Root does not exist; skipping: {root}")
            continue

        for hci_path in sorted(root.rglob("*.hci.json")):
            try:
                hci = _load_json(hci_path)
                if not isinstance(hci, dict):
                    raise ValueError("not a JSON object")
                hci = apply_final_score(
                    hci,
                    wip_anchor=args.wip_anchor,
                    wip_alpha=args.wip_alpha,
                    wip_cap=args.wip_cap,
                    recompute=args.recompute,
                )
                _save_json(hci_path, hci)
                updated += 1
            except Exception as exc:
                log(f"[WARN] Could not process {hci_path}: {exc}")
                skipped += 1

    log(
        f"[DONE] Updated {updated} file(s); skipped {skipped}. "
        f"finished_at={utc_now_iso()}Z"
    )


if __name__ == "__main__":
    main()
