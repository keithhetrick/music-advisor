#!/usr/bin/env python3
"""
ma_add_echo_to_hci_v1.py

For each .hci.json under a root:

- Find the matching .features.json in the same folder.
- Run the Tier 1 Historical Echo probe.
- Write a minimal summary block into the HCI JSON:

  "historical_echo_v1": {
    "primary_decade": "1985–1994",
    "primary_decade_neighbor_count": 9,
    "top_neighbor": {
      "year": 1993,
      "artist": "P.M. Dawn",
      "title": "Looking Through Patient Eyes",
      "distance": 0.654
    }
  }

Usage (from repo root):

    python tools/ma_add_echo_to_hci_v1.py \\
      --root features_output/2025/11/20 \\
      --year-max 2020
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()
HOME = str(Path.home())

from ma_audio_engine.adapters import (
    add_log_sandbox_arg,
    add_log_format_arg,
    add_preflight_arg,
    add_qa_policy_arg,
    apply_log_sandbox_env,
    apply_log_format_env,
    run_preflight_if_requested,
    is_backend_enabled,
    list_supported_backends,
    load_json_guarded,
    make_logger,
    load_log_settings,
    load_runtime_settings,
    require_file,
    validate_root_dir,
)
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from ma_audio_engine.adapters import di
from ma_audio_engine.schemas import dump_json
from ma_audio_engine.schemas import Features, HCI, HistoricalEcho
from tools.hci_echo_probe_from_spine_v1 import run_echo_probe_for_features
from tools.schema_utils import lint_json_file
from tools.echo_services import inject_echo_into_hci
from ma_config.paths import get_historical_echo_db_path

LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
_log = make_logger("echo_hci", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)
_QUIET = False


def _log_info(msg: str) -> None:
    if not _QUIET:
        _log(msg)


def _log_warn(msg: str) -> None:
    _log(msg)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Inject Tier 1 Historical Echo v1 summary into .hci.json files."
    )
    p.add_argument(
        "--root",
        required=True,
        help="Root directory containing per-track folders with *.hci.json + *.features.json.",
    )
    p.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help="Path to historical_echo SQLite DB.",
    )
    p.add_argument(
        "--table",
        default="spine_master_v1_lanes",
        help="Spine table name (default: spine_master_v1_lanes).",
    )
    p.add_argument(
        "--echo-tier",
        default="EchoTier_1_YearEnd_Top40",
        help="Echo tier filter (default: EchoTier_1_YearEnd_Top40).",
    )
    p.add_argument(
        "--year-min",
        type=int,
        default=1985,
        help="Minimum spine year to include (default: 1985).",
    )
    p.add_argument(
        "--year-max",
        type=int,
        default=2020,
        help="Maximum spine year to include (default: 2020; newer years sparse).",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of nearest neighbors to compute (default: 10).",
    )
    p.add_argument(
        "--tiers",
        default="tier1_modern,tier2_modern,tier3_modern",
        help="Comma list of tiers to search (default: tier1_modern,tier2_modern,tier3_modern). Supported: tier1_modern, tier2_modern, tier3_modern.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute echo and show what would happen, but do not modify files.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-warning output (warnings/errors still print).",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if lint warnings are encountered.",
    )
    add_qa_policy_arg(p)
    p.add_argument(
        "--use-tempo-confidence",
        action="store_true",
        help="Down-weight tempo axis when WIP tempo confidence is low (default: off).",
    )
    p.add_argument(
        "--tempo-confidence-threshold",
        type=float,
        default=0.4,
        help="Confidence score below which tempo is down-weighted (default: 0.4).",
    )
    p.add_argument(
        "--tempo-weight-low",
        type=float,
        default=0.3,
        help="Weight multiplier for tempo axis when confidence is low (default: 0.3).",
    )
    p.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    p.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(p)
    add_log_format_arg(p)
    add_preflight_arg(p)
    return p.parse_args()


def find_hci_files(root: Path) -> List[Path]:
    return sorted(root.rglob("*.hci.json"))


def pick_features_file(track_dir: Path) -> Optional[Path]:
    """
    Pick a .features.json in the same directory:

    - If exactly one, use it.
    - If multiple, pick the most recently modified.
    """
    candidates = list(track_dir.glob("*.features.json"))
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def compute_feature_freshness(feature_path: Path, hci_path: Path, meta: Dict[str, Any]) -> str:
    try:
        feature_mtime = feature_path.stat().st_mtime
        hci_mtime = hci_path.stat().st_mtime
    except Exception:
        return "unknown"

    if not meta.get("source_hash"):
        return "missing_source_hash"
    if feature_mtime > hci_mtime + 1e-3:
        return "feature_newer_than_hci"
    return "ok"


def compute_audio_feature_freshness(feature_path: Path, meta: Dict[str, Any]) -> str:
    audio_path = meta.get("source_audio")
    if not audio_path:
        return "missing_source_audio"
    try:
        audio_mtime = Path(audio_path).stat().st_mtime
        feature_mtime = feature_path.stat().st_mtime
    except Exception:
        return "unknown"
    if audio_mtime > feature_mtime + 1e-3:
        return "audio_newer_than_features"
    return "ok"


def load_feature_meta(path: Path, hci_path: Path) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    data = load_json_guarded(str(path), logger=_log_warn)
    if not data:
        _log_warn(f"[echo_hci]   WARN: could not read features JSON {path}")
        return meta
    try:
        feat = Features.from_json(path)
        meta["source_hash"] = feat.feature_pipeline_meta.source_hash
        meta["config_fingerprint"] = feat.feature_pipeline_meta.config_fingerprint
        meta["pipeline_version"] = feat.feature_pipeline_meta.pipeline_version
        meta["tempo_backend"] = feat.tempo_backend
        meta["tempo_backend_detail"] = feat.tempo_backend_detail
    except Exception as e:
        _log_warn(f"[echo_hci]   WARN: schema parse failed for {path}: {e}")
    try:
        meta["loudness_LUFS"] = data.get("loudness_LUFS")
        meta["loudness_LUFS_normalized"] = data.get("loudness_LUFS_normalized")
        meta["loudness_normalization_gain_db"] = data.get("loudness_normalization_gain_db")
        meta["normalized_for_features"] = data.get("normalized_for_features")
        meta["target_sample_rate"] = data.get("target_sample_rate")
        meta["tempo_primary"] = data.get("tempo_primary")
        meta["tempo_alt_half"] = data.get("tempo_alt_half")
        meta["tempo_alt_double"] = data.get("tempo_alt_double")
        meta["tempo_choice_reason"] = data.get("tempo_choice_reason")
        meta["tempo_confidence"] = data.get("tempo_confidence")
        meta["tempo_confidence_score"] = data.get("tempo_confidence_score")
        meta["tempo_confidence_score_raw"] = data.get("tempo_confidence_score_raw")
        meta["tempo_backend_source"] = data.get("tempo_backend_source")
        meta["tempo_backend_meta"] = data.get("tempo_backend_meta")
        meta["tempo_alternates"] = data.get("tempo_alternates")
        meta["tempo_candidates"] = data.get("tempo_candidates")
        meta["tempo_beats_count"] = data.get("tempo_beats_count")
        meta["sidecar_status"] = data.get("sidecar_status")
        meta["sidecar_warnings"] = data.get("sidecar_warnings")
        meta["key_confidence"] = data.get("key_confidence")
        meta["key_confidence_score_raw"] = data.get("key_confidence_score_raw")
        meta["key_candidates"] = data.get("key_candidates")
        meta["key_backend"] = data.get("key_backend")
        meta["source_mtime"] = data.get("source_mtime")
        meta["source_audio"] = data.get("source_audio")
        meta["processed_utc"] = data.get("processed_utc")
        meta["generated_utc"] = data.get("generated_utc")
        meta["cache_status"] = data.get("cache_status")
        meta["qa_gate"] = data.get("qa_gate")
        meta["feature_file_mtime"] = path.stat().st_mtime
        qa = data.get("qa") or {}
        meta["qa"] = {
            "peak_dbfs": qa.get("peak_dbfs"),
            "rms_dbfs": qa.get("rms_dbfs"),
            "clipping": qa.get("clipping"),
            "silence_ratio": qa.get("silence_ratio"),
            "status": qa.get("status"),
            "gate": qa.get("gate"),
        }
        meta["feature_freshness"] = compute_feature_freshness(path, hci_path, meta)
        meta["audio_feature_freshness"] = compute_audio_feature_freshness(path, meta)

        backend_detail = meta.get("tempo_backend_detail") or meta.get("tempo_backend")
        supported = list_supported_backends()
        if backend_detail and backend_detail not in supported:
            _log_warn(
                f"[echo_hci]   WARN: tempo backend '{backend_detail}' not in registry {supported}; "
                "ensure config/backend_registry.json is aligned."
            )
        elif backend_detail and not is_backend_enabled(backend_detail):
            _log_warn(
                f"[echo_hci]   WARN: tempo backend '{backend_detail}' is disabled in registry; "
                "features may be using a non-preferred backend."
            )
    except Exception:
        _log_warn(f"[echo_hci]   WARN: failed to parse feature meta from {path}")
    return meta


def trim_neighbors(echo_data: Dict[str, Any], max_keep: int) -> Dict[str, Any]:
    trimmed = dict(echo_data)
    for key in ("neighbors", "tier1_neighbors", "tier2_neighbors", "tier3_neighbors"):
        if key in trimmed and isinstance(trimmed[key], list):
            trimmed[key] = trimmed[key][:max_keep]
    return trimmed


def build_hist_block(echo_data: Dict[str, Any]) -> Dict[str, Any]:
    neighbors: List[Dict[str, Any]] = echo_data.get("neighbors", []) or []
    decade_counts: Dict[str, int] = echo_data.get("decade_counts", {}) or {}
    neighbor_filter_notes = echo_data.get("neighbor_filter_notes")

    if not neighbors:
        return {
            "primary_decade": None,
            "primary_decade_neighbor_count": 0,
            "top_neighbor": None,
            "neighbors": [],
            "tier1_neighbors": [],
            "tier2_neighbors": [],
            "tier3_neighbors": [],
            "tier_notes": {
                "tier1_modern": "Modern Year-End Top 40 (1985–2024): strongest echo.",
                "tier2_modern": "Modern Year-End Hot 100 Top 100 (1985–2024): secondary echo.",
                "tier3_modern": "Modern Year-End Hot 100 Top 200 (1985–2024): tertiary echo (weakest ring).",
            },
            "neighbor_filter_notes": neighbor_filter_notes,
        }

    primary_decade, count_primary = sorted(
        decade_counts.items(),
        key=lambda x: (-x[1], x[0]),
    )[0]

    top = neighbors[0]
    top_neighbor = {
        "year": top["year"],
        "artist": top["artist"],
        "title": top["title"],
        "distance": top["distance"],
    }

    return {
        "primary_decade": primary_decade,
        "primary_decade_neighbor_count": int(count_primary),
        "top_neighbor": top_neighbor,
        "neighbors": neighbors,
        "tier1_neighbors": echo_data.get("tier1_neighbors", []),
        "tier2_neighbors": echo_data.get("tier2_neighbors", []),
        "tier3_neighbors": echo_data.get("tier3_neighbors", []),
        "tier_notes": {
            "tier1_modern": "Modern Year-End Top 40 (1985–2024): strongest echo.",
            "tier2_modern": "Modern Year-End Hot 100 Top 100 (1985–2024): secondary echo.",
            "tier3_modern": "Modern Year-End Hot 100 Top 200 (1985–2024): tertiary echo (weakest ring).",
        },
        "neighbor_filter_notes": neighbor_filter_notes,
    }


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    dump_json(tmp_path, payload)
    tmp_path.replace(path)


def warn_if_hci_schema_sparse(path: Path, payload: Dict[str, Any]) -> None:
    required = {"historical_echo_v1", "historical_echo_meta", "feature_pipeline_meta"}
    missing = [k for k in required if k not in payload]
    if missing:
        _log_warn(f"[echo_hci]   WARN: {path.name} missing keys {missing} before write")
    he = payload.get("historical_echo_v1")
    if not isinstance(he, dict) or "neighbors" not in he:
        _log_warn(f"[echo_hci]   WARN: {path.name} historical_echo_v1 missing neighbors")


def process_hci_file(hci_path: Path, args: argparse.Namespace) -> list[str]:
    track_dir = hci_path.parent
    warnings: list[str] = []
    if not args.quiet:
        _log_info(f"[echo_hci] Processing: {hci_path}")

    features_path = pick_features_file(track_dir)
    if not features_path:
        _log_warn(f"[echo_hci]   WARN: No .features.json found in {track_dir}, skipping.")
        warnings.append(f"{hci_path.name}:missing_features")
        return warnings

    if not require_file(str(hci_path), logger=_log_warn):
        return warnings
    if not require_file(str(features_path), logger=_log_warn):
        _log_warn(f"[echo_hci]   WARN: missing features file for {track_dir}")
        warnings.append(f"{hci_path.name}:missing_features")
        return warnings
    data = load_json_guarded(str(hci_path), logger=_log_warn)
    if not data:
        _log_warn(f"[echo_hci]   ERROR reading {hci_path}")
        warnings.append(f"{hci_path.name}:read_error")
        return warnings

    feature_meta = load_feature_meta(features_path, hci_path)
    if args.qa_policy == "strict":
        gate = (feature_meta.get("qa_gate") or "").lower()
        if gate and gate not in {"pass", "ok"}:
            _log_warn(f"[echo_hci]   SKIP: QA gate '{gate}' failed strict policy for {features_path.name}")
            warnings.append(f"{features_path.name}:qa_gate:{gate}")
            return warnings
    missing_keys = []
    if not feature_meta.get("source_hash"):
        missing_keys.append("source_hash")
    if not feature_meta.get("config_fingerprint"):
        missing_keys.append("config_fingerprint")
    if not feature_meta.get("pipeline_version"):
        missing_keys.append("pipeline_version")
    if missing_keys:
        _log_warn(f"[echo_hci]   WARN: feature meta missing {missing_keys} for {features_path}")
        warnings.extend([f"{features_path.name}:missing:{k}" for k in missing_keys])

    # Populate pipeline meta early so lint does not warn about missing key.
    data.setdefault("feature_pipeline_meta", feature_meta)

    warn_feature, _ = lint_json_file(features_path, kind="features")
    warn_hci, _ = lint_json_file(hci_path, kind="hci")
    if warn_feature:
        _log_warn(f"[echo_hci]   WARN feature lint ({features_path.name}): {warn_feature}")
        if args.strict:
            raise SystemExit(f"lint failed for {features_path}: {warn_feature}")
    if warn_hci:
        _log_warn(f"[echo_hci]   WARN hci lint ({hci_path.name}): {warn_hci}")
        if args.strict:
            raise SystemExit(f"lint failed for {hci_path}: {warn_hci}")

    echo_data = run_echo_probe_for_features(
        features_path=str(features_path),
        db=args.db,
        table=args.table,
        echo_tier=args.echo_tier,
        year_min=args.year_min,
        year_max=args.year_max,
        top_k=args.top_k,
        tiers=args.tiers,
        use_tempo_confidence=args.use_tempo_confidence,
        tempo_confidence_threshold=args.tempo_confidence_threshold,
        tempo_weight_low=args.tempo_weight_low,
    )

    # Persist full neighbor payload alongside the track
    neighbors_out = track_dir / f"{track_dir.name}.neighbors.json"
    data, inject_warns = inject_echo_into_hci(data, feature_meta, echo_data, neighbors_out, max_neighbors_inline=4)
    warnings.extend(inject_warns)

    hist_block = data.get("historical_echo_v1") or {}
    if args.dry_run:
        _log_info(f"[echo_hci]   DRY RUN: would update {hci_path}")
        _log_info(f"[echo_hci]   Summary: {hist_block}")
        return warnings

    # Atomic pretty JSON write
    warn_if_hci_schema_sparse(hci_path, data)
    atomic_write_json(hci_path, data)
    lint_warns, _ = lint_json_file(hci_path, "hci")
    warnings.extend([f"{hci_path.name}:{w}" for w in lint_warns])
    if not args.quiet:
        warn_suffix = f" (warnings={lint_warns})" if lint_warns else ""
        _log_info(f"[echo_hci]   Updated {hci_path}{warn_suffix}")
        _log_info(f"[echo_hci]   Summary: {hist_block}")
    return warnings


def main() -> None:
    args = parse_args()
    global _log, _QUIET
    _QUIET = bool(args.quiet)
    apply_log_sandbox_env(args)
    apply_log_format_env(args)
    run_preflight_if_requested(args)
    # Align runtime/config defaults across CLIs.
    _ = load_runtime_settings(args)
    settings = load_log_settings(args)
    redact_flag = settings.log_redact or LOG_REDACT
    redact_values = settings.log_redact_values or LOG_REDACT_VALUES
    _log = di.make_logger("echo_hci", structured=os.getenv("LOG_JSON") == "1", defaults={"tool": "echo_hci"}, redact=redact_flag, secrets=redact_values)
    allowed_qa = {"default", "lenient", "strict"}
    if not args.qa_policy or args.qa_policy not in allowed_qa:
        args.qa_policy = os.getenv("QA_POLICY", "default")
    if args.qa_policy not in allowed_qa:
        args.qa_policy = "default"
    root = validate_root_dir(args.root, logger=_log_warn)
    if root is None:
        return
    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        log_stage_start(
            _log,
            "echo_hci",
            root=str(root),
            qa_policy=args.qa_policy,
            year_max=args.year_max,
            quiet=bool(args.quiet),
        )

    hci_files = find_hci_files(root)
    if not hci_files:
        _log_info(f"[echo_hci] No *.hci.json files found under {root}")
        return

    def redact(path: Path) -> str:
        return str(path).replace(HOME, "~")

    lint_failures = 0
    warnings: list[str] = []
    _log_info(f"[echo_hci] Found {len(hci_files)} *.hci.json under {redact(root)}")
    for hci_path in hci_files:
        _log_info(f"[echo_hci] Processing: {redact(hci_path)}")
        try:
            file_warns = process_hci_file(hci_path, args)
            warnings.extend(file_warns)
        except SystemExit as exc:
            lint_failures += 1
            if args.strict:
                raise
            _log_warn(f"[echo_hci] strict lint failure ignored (strict disabled): {exc}")
    status = "ok"
    if (lint_failures or warnings) and args.strict:
        status = "error"
    if os.getenv("LOG_JSON") == "1":
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        log_stage_end(
            _log,
            "echo_hci",
            status=status,
            root=str(root),
            count=len(hci_files),
            lint_failures=lint_failures,
            duration_ms=duration_ms,
            warnings=warnings,
        )
        _log("end", {"event": "end", "tool": "echo_hci", "root": str(root), "status": "ok", "count": len(hci_files), "duration_ms": duration_ms})
    if (lint_failures or warnings) and args.strict:
        raise SystemExit("strict mode: lint warnings present")


if __name__ == "__main__":
    raise SystemExit(main())
