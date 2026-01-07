#!/usr/bin/env python3
"""
ma_add_echo_to_client_rich_v1.py

For each .client.rich.txt under a root:

- Find the matching .features.json in the same folder.
- Run the Tier 1 Historical Echo probe.
- Inject:

  1) A header line, e.g.:
     # HISTORICAL_ECHO_V1: primary_decade=1995–2004 (5/10) | closest=1998 – Jon B — They Don't Know (dist=0.314)

  2) A full JSON block inside the /audio import { ... } object:
     "historical_echo_v1": {
       "wip_features": {...},
       "decade_counts": {...},
       "neighbors": [...]
     }

Usage (from repo root):

  python tools/hci/ma_add_echo_to_client_rich_v1.py \\
    --root features_output/2025/11/20/Some Track \\
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

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parent.parent
SRC_PATH = REPO_ROOT / "src"
from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()
HOME = str(Path.home())

from ma_audio_engine.adapters import (
    add_log_sandbox_arg,
    add_qa_policy_arg,
    add_log_format_arg,
    add_preflight_arg,
    apply_log_sandbox_env,
    apply_log_format_env,
    run_preflight_if_requested,
    list_supported_backends,
    is_backend_enabled,
    load_json_guarded,
    load_log_settings,
    load_runtime_settings,
    require_file,
    utc_now_iso,
    validate_root_dir,
)
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from ma_audio_engine.adapters import di
from ma_audio_engine.schemas import dump_json, CLIENTRich, HCI, Features
from ma_audio_engine.schemas import lint_client_rich_text
from tools import names
from tools.hci_echo_probe_from_spine_v1 import run_echo_probe_for_features
from tools.schema_utils import lint_json_file
from tools.echo_services import inject_echo_into_client, write_neighbors_file
from ma_config.paths import get_historical_echo_db_path
from shared.ma_utils.logger_factory import get_configured_logger

# Optional client-rich support; falls back to generic structures if the schema package
# hasn't been updated yet.
try:  # pragma: no cover - guarded import
    from ma_audio_engine.schemas import CLIENTRich, lint_client_rich_text  # type: ignore
except Exception:  # noqa: BLE001
    CLIENTRich = CLIENTRich  # type: ignore
    lint_client_rich_text = lint_client_rich_text  # type: ignore

_log = get_configured_logger("echo_inject")
_QUIET = False
_SUPPORTED_BACKENDS = set(list_supported_backends())
# Calibration/version tags for transparency in rich text; override via env.
CAL_VERSION = os.getenv("HCI_CAL_VERSION", "HCI_v1 2025Q4")
CAL_DATE = os.getenv("HCI_CAL_DATE", "2025-11-17")


def _log_info(msg: str) -> None:
    if not _QUIET:
        _log(msg)


def _log_warn(msg: str) -> None:
    _log(msg)


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def warn_if_client_schema_sparse(path: Path, payload: Dict[str, Any]) -> None:
    required = {"historical_echo_v1", "historical_echo_meta"}
    missing = [k for k in required if k not in payload]
    if missing:
        _log_warn(f"[echo_inject]   WARN: {path.name} missing keys {missing} before write")
    he = payload.get("historical_echo_v1")
    if not isinstance(he, dict) or "neighbors" not in he:
        _log_warn(f"[echo_inject]   WARN: {path.name} historical_echo_v1 missing neighbors")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=f"Inject Tier 1 Historical Echo v1 into .{names.CLIENT_TOKEN}.rich.txt files."
    )
    p.add_argument(
        "--root",
        required=True,
        help=f"Root directory containing per-track folders with *.{names.CLIENT_TOKEN}.rich.txt + *.features.json.",
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
        help="Exit non-zero if lint warnings are found in input .client.rich.txt",
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


def find_client_rich_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for pattern in names.client_rich_globs():
        files.extend(root.rglob(pattern))
    return sorted(set(files))


def _is_client_path(path: Path) -> bool:
    return ".client." in path.name


def pick_features_file(track_dir: Path) -> Optional[Path]:
    candidates = list(track_dir.glob("*.features.json"))
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def pick_hci_file(track_dir: Path) -> Optional[Path]:
    candidates = list(track_dir.glob("*.hci.json"))
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def compute_feature_freshness(feature_path: Path, parent_path: Path, meta: Dict[str, Any]) -> str:
    try:
        feature_mtime = feature_path.stat().st_mtime
        parent_mtime = parent_path.stat().st_mtime
    except Exception:
        return "unknown"

    if not meta.get("source_hash"):
        return "missing_source_hash"
    if feature_mtime > parent_mtime + 1e-3:
        return "feature_newer_than_parent"
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


def load_feature_meta(path: Path, parent_path: Path) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    try:
        data = load_json_guarded(str(path), logger=_log_warn)
        if not data:
            return meta
        meta["loudness_LUFS"] = data.get("loudness_LUFS")
        meta["loudness_LUFS_normalized"] = data.get("loudness_LUFS_normalized")
        meta["loudness_normalization_gain_db"] = data.get("loudness_normalization_gain_db")
        meta["normalized_for_features"] = data.get("normalized_for_features")
        meta["pipeline_version"] = data.get("pipeline_version")
        meta["config_fingerprint"] = data.get("config_fingerprint")
        meta["target_sample_rate"] = data.get("target_sample_rate")
        meta["tempo_primary"] = data.get("tempo_primary")
        meta["tempo_alt_half"] = data.get("tempo_alt_half")
        meta["tempo_alt_double"] = data.get("tempo_alt_double")
        meta["tempo_choice_reason"] = data.get("tempo_choice_reason")
        meta["tempo_confidence"] = data.get("tempo_confidence")
        meta["tempo_confidence_score"] = data.get("tempo_confidence_score")
        meta["tempo_confidence_score_raw"] = data.get("tempo_confidence_score_raw")
        meta["tempo_backend"] = data.get("tempo_backend")
        meta["tempo_backend_source"] = data.get("tempo_backend_source")
        meta["tempo_backend_detail"] = data.get("tempo_backend_detail")
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
        meta["source_hash"] = data.get("source_hash")
        meta["source_mtime"] = data.get("source_mtime")
        meta["source_audio"] = data.get("source_audio")
        meta["source_audio_info"] = data.get("source_audio_info")
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
        meta["feature_freshness"] = compute_feature_freshness(path, parent_path, meta)
        meta["audio_feature_freshness"] = compute_audio_feature_freshness(path, meta)
        backend_detail = meta.get("tempo_backend_detail") or meta.get("tempo_backend")
        if backend_detail and backend_detail not in _SUPPORTED_BACKENDS:
            _log_warn(
                f"[echo_inject]   WARN: {path.name} tempo backend '{backend_detail}' not in registry supported set {_SUPPORTED_BACKENDS}"
            )
        if backend_detail and not is_backend_enabled(backend_detail):
            _log_warn(
                f"[echo_inject]   WARN: {path.name} tempo backend '{backend_detail}' is disabled in registry"
            )
    except Exception:
        pass
    return meta


def _score_to_tier(final_score: Optional[float]) -> str:
    if final_score is None:
        return "WIP-unknown"
    if final_score >= 0.82:
        return "WIP-A+"
    if final_score >= 0.72:
        return "WIP-A"
    if final_score >= 0.62:
        return "WIP-B+"
    if final_score >= 0.52:
        return "WIP-B"
    return "WIP-C"


def _tier_description(tier: str) -> str:
    desc_map = {
        "WIP-A+": "Very strong hit draft (historical-echo audio)",
        "WIP-A": "Strong, hit-leaning draft (historical-echo audio)",
        "WIP-B+": "Good draft with solid echo alignment",
        "WIP-B": "Work-in-progress; moderate echo alignment",
        "WIP-C": "Early work; weak echo alignment",
        "WIP-unknown": "Unknown tier (historical-echo audio)",
    }
    return desc_map.get(tier, "Historical-echo audio tier")


CAL_VERSION = os.getenv("HCI_CAL_VERSION", "HCI_v1 2025Q4")


def build_hci_header_lines(hci_meta: Dict[str, Any], client_json: Optional[Dict[str, Any]] = None) -> Optional[List[str]]:
    """
    Build a small HCI header block (optional) that sits near the top of the file.
    Kept concise: final tier + source, with optional interpretation/notes.
    """
    meta = dict(hci_meta or {})
    # Derive tier from final_score when present
    final_score = meta.get("HCI_v1_final_score") or meta.get("final_score")
    tier = meta.get("HCI_v1_final_tier") or meta.get("tier") or _score_to_tier(final_score)
    tier_desc = meta.get("HCI_v1_final_tier_desc") or _tier_description(tier)
    # Prefer explicit source, else generated_by, else pack_writer
    source = meta.get("final_source") or meta.get("source") or (client_json or {}).get("generated_by") or "pack_writer"
    interp = meta.get("HCI_v1_interpretation") or (
        "Historical-echo-centric audio metric. Measures how this audio file’s features align with "
        "long-running US Pop hit archetypes; it does NOT predict commercial success, streams, "
        "virality, or cultural impact. It is a diagnostic tool for audio shape and historical echo, "
        "not a hit-prediction oracle."
    )
    notes = meta.get("HCI_v1_notes") or (
        "Sanity check examples: a WIP copy of The Weeknd's 'Blinding Lights' (most-streamed track) scores around final=0.773 "
        "mid-scale on HCI_v1, while Miley Cyrus's 'Flowers' can score high (around final=0.881). Calibrated scores can occasionally "
        "approach 1.0; that reflects historical-echo shape, not popularity. Scores and tiers may shift when the spine "
        "or calibration is refreshed."
    )
    lines = [
        "",
        "# ==== HCI INTERPRETATION ====",
        f"# HCI_V1_FINAL: tier={tier} — {tier_desc} | source={source}",
        f"#   calibration: {CAL_VERSION} (date={CAL_DATE}; scores/tiers may shift when spine/calibration refreshes)",
        f"#   interpretation: {interp}",
        f"#   notes: {notes}",
        "",
    ]
    return lines


def extract_client_rich(content: str, rich_cls=CLIENTRich) -> CLIENTRich:
    marker = "/audio import"
    idx = content.find(marker)
    if idx == -1:
        raise ValueError(f"No '/audio import' marker found in .{names.CLIENT_TOKEN}.rich.txt")
    json_start = content.find("{", idx)
    if json_start == -1:
        raise ValueError(f"No '{{' found after '/audio import' in .{names.CLIENT_TOKEN}.rich.txt")
    # Only grab the JSON block following /audio import to avoid trailing text
    brace_depth = 0
    end_idx = None
    for i, ch in enumerate(content[json_start:], start=json_start):
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0:
                end_idx = i + 1
                break
    if end_idx is None:
        raise ValueError(f"Unbalanced braces in .{names.CLIENT_TOKEN}.rich.txt after /audio import")
    json_str = content[json_start:end_idx]
    payload = json.loads(json_str)
    return rich_cls(text=content, hci_score=None, philosophy=None, echo_summary=None), payload


def rebuild_client_rich_content(
    orig_content: str,
    updated_json: Dict[str, Any],
    neighbor_lines: str,
    prefix_lines: List[str],
    hci_header_lines: Optional[List[str]] = None,
    audio_header_lines: Optional[List[str]] = None,
    neighbor_meta_lines: Optional[List[str]] = None,
) -> str:
    marker = "/audio import"
    idx_audio = orig_content.find(marker)
    if idx_audio == -1:
        raise ValueError(f"No '/audio import' marker found in .{names.CLIENT_TOKEN}.rich.txt")
    json_start = orig_content.find("{", idx_audio)
    if json_start == -1:
        raise ValueError(f"No '{{' found after '/audio import' in .{names.CLIENT_TOKEN}.rich.txt")

    header_text = orig_content[:idx_audio]
    import_prefix = orig_content[idx_audio:json_start]

    existing_lines = header_text.rstrip("\n").splitlines()
    existing_lines = [
      ln for ln in existing_lines
      if not ln.lstrip().startswith("# HISTORICAL_ECHO_V1:")
      and not ln.lstrip().startswith("# ECHO SUMMARY:")
      and not ln.lstrip().startswith("# HCI_V1_FINAL:")
      and not ln.lstrip().startswith("# HCI_V1_META:")
      and not ln.lstrip().startswith("# ==== HISTORICAL ECHO V1 ====")
      and not ln.lstrip().startswith("# ==== HCI INTERPRETATION ====")
      and not ln.lstrip().startswith("# ==== MUSIC ADVISOR")
      and not ln.lstrip().startswith("# Author:")
      and not ln.lstrip().startswith("# Version:")
      and not ln.lstrip().startswith("# Generated:")
      and not ln.lstrip().startswith("# STRUCTURE_POLICY:")
      and not ln.lstrip().startswith("# GOLDILOCKS_POLICY:")
      and not ln.lstrip().startswith("# HCI_POLICY:")
      and not ln.lstrip().startswith("# CONTEXT:")
      and not ln.lstrip().startswith("# HCI_V1_SUMMARY:")
      and not ln.lstrip().startswith("# AUDIO_PIPELINE:")
      and not f"Music Advisor — Paste below into {names.client_header_label()}" in ln
    ]
    if prefix_lines:
        # When we supply a full header (from the current file), avoid re-appending
        # filtered leftovers that would duplicate sections.
        existing_lines = []

    header_lines: List[str] = []
    header_lines.extend(prefix_lines)
    if hci_header_lines:
        header_lines.extend(hci_header_lines)
    if audio_header_lines:
        header_lines.append("# ====================================")
        header_lines.extend(audio_header_lines)
    if neighbor_meta_lines:
        header_lines.append("#")
        header_lines.append("# ====================================")
        header_lines.extend(neighbor_meta_lines)
        header_lines.append("# ====================================")
        header_lines.append("")
    header_lines.extend(existing_lines)
    # Add neighbor summary block after header lines for quick scan
    header_lines.extend(neighbor_lines.splitlines())

    # Add a blank spacer after PHILOSOPHY line (if present) for readability
    for i, ln in enumerate(header_lines):
        if ln.lstrip().startswith("# PHILOSOPHY"):
            if i + 1 >= len(header_lines) or header_lines[i + 1].strip() != "":
                header_lines.insert(i + 1, "")
            # Ensure an extra spacer after the philosophy line to match desired layout
            if i + 2 >= len(header_lines) or header_lines[i + 2].strip() != "":
                header_lines.insert(i + 2, "")
            break

    # Preserve spacing, but treat comment-only "#" as blank spacers; collapse consecutive blanks
    cleaned: List[str] = []
    for ln in header_lines:
        if ln.strip() == "" and cleaned and cleaned[-1].strip() == "":
            continue
        cleaned.append(ln)
    header_lines = cleaned

    new_header = "\n".join(header_lines) + "\n\n"  # blank line before /audio import
    new_json_str = json.dumps(updated_json, indent=2)

    return new_header + import_prefix + new_json_str + "\n"


def clean_header_spacing(text: str) -> str:
    """
    Collapse duplicate blank/comment-only spacer lines in the header section.
    """
    marker = "\n/audio import"
    idx = text.find(marker)
    if idx == -1:
        return text
    header = text[:idx]
    body = text[idx:]
    lines = header.splitlines()
    cleaned: List[str] = []
    in_echo_block = False
    for ln in lines:
        if ln.lstrip().startswith("# ==== HISTORICAL ECHO V1 ===="):
            in_echo_block = True
        if in_echo_block:
            cleaned.append(ln)
            continue
        if ln.strip() == "#":
            ln = ""
        if ln.strip() == "" and cleaned and cleaned[-1].strip() == "":
            continue
        cleaned.append(ln)
    return "\n".join(cleaned).rstrip() + "\n" + body


def build_default_context_header(
    client_json: Dict[str, Any],
    hci_meta: Dict[str, Any],
) -> List[str]:
    """Populate a stable header so client.rich.txt files share the same shape as legacy outputs."""
    region = client_json.get("region") or "US"
    profile = client_json.get("profile") or "Pop"
    audio_name = client_json.get("audio_name") or client_json.get("inputs", {}).get("paths", {}).get("source_audio") or "unknown"
    final_score = hci_meta.get("final_score")
    raw_score = hci_meta.get("raw_score")
    calibrated = hci_meta.get("calibrated_score")
    role = hci_meta.get("hci_role") or "unknown"
    generated = utc_now_iso()
    lines = [
        "# ==== MUSIC ADVISOR - SONG CONTEXT ====",
        "# Author: Keith Hetrick - injects HCI+Echo context into .client.rich.txt",
        "# Version: HCI+Echo context v1.1",
        f"# Generated: {generated}",
        "# ====================================",
        "# STRUCTURE_POLICY: mode=optional | reliable=false | use_ttc=false | use_exposures=false",
        "# GOLDILOCKS_POLICY: active=true | priors={'Market': 0.5, 'Emotional': 0.5} | caps={'Market': 0.58, 'Emotional': 0.58}",
        "# HCI_POLICY: HCI_v1_final_score is canonical; raw/calibrated are provided for transparency only.",
        f"# CONTEXT: region={region}, profile={profile}, audio_name={audio_name}",
        f"# HCI_V1_SUMMARY: final={final_score} | role={role} | raw={raw_score} | calibrated={calibrated}",
        "",
        "# PHILOSOPHY: The Top 40 of today is the Top 40 of ~40 years ago, re-parameterized. HCI_v1 is a measure of Historical Echo — not a hit predictor.",
        "",
    ]
    return lines


def build_audio_metadata_lines(feature_meta: Dict[str, Any]) -> List[str]:
    """Optional audio metadata block from the features file."""
    lines: List[str] = []
    src_path = feature_meta.get("source_audio")
    info = feature_meta.get("source_audio_info") or {}
    if not src_path and not info:
        return lines
    if src_path:
        lines.append(f"# source_audio: {src_path}")
        try:
            size_bytes = Path(src_path).expanduser().stat().st_size
            lines.append(f"# file_size: {size_bytes} bytes (~{size_bytes/1_000_000:.2f} MB)")
        except Exception:
            pass
    fmt = info.get("orig_format") or info.get("format")
    subtype = info.get("orig_subtype") or info.get("subtype")
    sr = info.get("orig_sample_rate") or info.get("sample_rate")
    ch = info.get("orig_channels") or info.get("channels")
    dur = info.get("orig_duration_sec") or info.get("duration_sec")
    container_parts = []
    if fmt:
        container_parts.append(f"format={fmt}")
    if subtype:
        container_parts.append(f"subtype={subtype}")
    if sr:
        container_parts.append(f"sr={sr}")
    if ch:
        container_parts.append(f"ch={ch}")
    if dur:
        container_parts.append(f"duration={dur}")
    if container_parts:
        lines.append("# container: " + " | ".join(container_parts))
    return lines


def build_echo_header_line(echo_data: Dict[str, Any]) -> str:
    neighbors: List[Dict[str, Any]] = echo_data.get("neighbors", []) or []
    # Sort globally by distance (closest first), regardless of tier priority.
    neighbors = sorted(neighbors, key=lambda n: n.get("distance", 0))
    decade_counts: Dict[str, int] = echo_data.get("decade_counts", {}) or {}

    if not neighbors:
        return "# ECHO SUMMARY: no_neighbors_found (no Tier 1 rows with usable audio)"

    primary_decade = sorted(
        decade_counts.items(),
        key=lambda x: (-x[1], x[0]),
    )[0][0]

    top = neighbors[0]
    count_primary = decade_counts.get(primary_decade, 0)
    total_neighbors = len(neighbors)
    tiers_used = sorted({n.get("tier", "tier1_modern") for n in neighbors})
    tiers_str = ",".join(tiers_used)

    return (
        "# ECHO SUMMARY: "
        f"tiers={tiers_str} | "
        f"primary_decade={primary_decade} ({count_primary}/{total_neighbors}) | "
        f"closest=({top['tier']}) {top['year']} – {top['artist']} — {top['title']} "
        f"(dist={top['distance']:.6f})"
    )


def build_neighbor_lines(echo_data: Dict[str, Any], summary_line: str, max_neighbors: int = 8) -> str:
    neighbors: List[Dict[str, Any]] = echo_data.get("neighbors", []) or []
    # Sort globally by distance (closest first), regardless of tier priority.
    neighbors = sorted(neighbors, key=lambda n: n.get("distance", 0))
    filter_notes = echo_data.get("neighbor_filter_notes") or {}
    lines = [
        "# ==== HISTORICAL ECHO V1 ====",
        summary_line,
        "# NEIGHBORS (deduped across tiers; sorted by dist, closest first)",
        "# Legend: tier1=Top40, tier2=Top100, tier3=Top200",
        "# dist: lower is closer (z-scored Euclidean on tempo/valence/energy/loudness)",
        "# feature_source: where features came from (e.g., essentia_local, yamaerenay)",
        "#",
    ]
    if filter_notes:
        lines.append(f"# neighbor_filter_notes: {filter_notes}")
    if not neighbors:
        lines.append("# HISTORICAL_ECHO_NEIGHBORS: none")
        return "\n".join(lines)
    header = f"#   {'#':>2}  {'tier':<10} {'dist':>6}  {'year':>4}  {'artist':<20}  {'title':<32}"
    lines.append(header)
    lines.append("#   " + "-" * (len(header) - 3))
    for idx, n in enumerate(neighbors[:max_neighbors], start=1):
        lines.append(
            "#   "
            f"{idx:>2}  "
            f"{n.get('tier',''):10.10} "
            f"{n.get('distance',0):>6.3f}  "
            f"{n.get('year',''):>4}  "
            f"{(n.get('artist') or '')[:20]:<20}  "
            f"{(n.get('title') or '')[:32]:<32}"
        )
    # Tier-wise mini-blocks (up to 3 per tier)
    lines.append("#")  # spacer
    tier_buckets: Dict[str, List[Dict[str, Any]]] = {}
    for n in neighbors:
        tier_buckets.setdefault(n.get("tier", "tier1_modern"), []).append(n)
    lines.append("# -- Per-tier snapshots (1985–2024 reference) --")
    for tier_label in ("tier1_modern", "tier2_modern", "tier3_modern"):
        if tier_label not in tier_buckets:
            continue
        lines.append(f"# {tier_label}:")
        for n in sorted(tier_buckets[tier_label], key=lambda n: n.get("distance", 0))[:4]:
            lines.append(
                "#     "
                f"{n.get('year',''):>4}  "
                f"{(n.get('artist') or '')[:20]:<20}  "
                f"{(n.get('title') or '')[:32]:<32}  "
                f"dist={n.get('distance',0):.3f}"
            )
    return "\n".join(lines)


def trim_neighbors(echo_data: Dict[str, Any], max_keep: int) -> Dict[str, Any]:
    trimmed = dict(echo_data)
    for key in ("neighbors", "tier1_neighbors", "tier2_neighbors", "tier3_neighbors"):
        if key in trimmed and isinstance(trimmed[key], list):
            trimmed[key] = trimmed[key][:max_keep]
    return trimmed


def process_client_rich_file(
    client_path: Path,
    args: argparse.Namespace,
) -> list[str]:
    hci_header_lines: List[str] = []
    audio_header_lines: List[str] = []
    neighbor_meta_lines: List[str] = []
    track_dir = client_path.parent
    if not args.quiet:
        _log_info(f"[echo_inject] Processing: {client_path}")

    warnings: list[str] = []
    lint_fn = lint_client_rich_text if _is_client_path(client_path) else lint_client_rich_text
    lint_warnings = lint_fn(client_path.read_text())
    if lint_warnings:
        warnings.extend([f"{client_path.name}:{w}" for w in lint_warnings])
        _log_warn(f"[echo_inject]   LINT WARN ({client_path.name}): {lint_warnings}")
        if args.strict:
            raise SystemExit(f"lint failed for {client_path}: {lint_warnings}")

    features_path = pick_features_file(track_dir)
    if not features_path:
        _log_warn(f"[echo_inject]   WARN: No .features.json found in {track_dir}, skipping.")
        return warnings
    if not require_file(str(client_path), logger=_log_warn):
        return warnings
    if not require_file(str(features_path), logger=_log_warn):
        return warnings

    orig_content = client_path.read_text()
    try:
        rich_cls = CLIENTRich if _is_client_path(client_path) else CLIENTRich
        client_obj, client_json = extract_client_rich(orig_content, rich_cls=rich_cls)
    except Exception as e:
        _log_warn(f"[echo_inject]   ERROR parsing JSON from {client_path}: {e}")
        return warnings

    warn_feature, _ = lint_json_file(features_path, kind="features")
    warn_hci: List[str] = []

    hci_path = pick_hci_file(track_dir)
    hci_meta = {}
    if hci_path:
        if require_file(str(hci_path), logger=_log_warn):
            try:
                hci_obj = HCI.from_json(hci_path)
                hci_meta = {
                    "HCI_v1_final_tier": hci_obj.historical_echo_meta.get("tier") if isinstance(hci_obj.historical_echo_meta, dict) else None,
                    "final_source": hci_obj.historical_echo_meta.get("final_source") if isinstance(hci_obj.historical_echo_meta, dict) else None,
                    "HCI_v1_interpretation": hci_obj.historical_echo_meta.get("HCI_v1_interpretation") if isinstance(hci_obj.historical_echo_meta, dict) else None,
                    "HCI_v1_notes": hci_obj.historical_echo_meta.get("HCI_v1_notes") if isinstance(hci_obj.historical_echo_meta, dict) else None,
                    "final_score": hci_obj.HCI_v1_final_score,
                    "raw_score": hci_obj.historical_echo_meta.get("raw_score") if isinstance(hci_obj.historical_echo_meta, dict) else None,
                    "calibrated_score": hci_obj.historical_echo_meta.get("calibrated_score") if isinstance(hci_obj.historical_echo_meta, dict) else None,
                    "hci_role": hci_obj.HCI_v1_role,
                }
            except Exception as e:  # noqa: BLE001
                _log_warn(f"[echo_inject]   WARN: failed to read {hci_path}: {e}")
            else:
                warn_hci, _ = lint_json_file(hci_path, kind="hci")
    # Provide a sensible default source from the current client JSON (pack_writer)
    hci_meta.setdefault("source", client_json.get("generated_by") or "pack_writer")

    # Always use the richer loader so AUDIO_PIPELINE gets populated.
    # The schema parse is still useful for validation, but we don't limit
    # ourselves to the small subset of fields in Features.from_json.
    feature_meta = load_feature_meta(features_path, client_path)
    try:
        feat_obj = Features.from_json(features_path)
        # If schema fields are present, patch them in (they may be stricter
        # than what load_feature_meta pulled from raw JSON).
        feature_meta.setdefault("source_hash", feat_obj.feature_pipeline_meta.source_hash)
        feature_meta.setdefault("config_fingerprint", feat_obj.feature_pipeline_meta.config_fingerprint)
        feature_meta.setdefault("pipeline_version", feat_obj.feature_pipeline_meta.pipeline_version)
        feature_meta.setdefault("tempo_backend", feat_obj.tempo_backend)
        feature_meta.setdefault("tempo_backend_detail", feat_obj.tempo_backend_detail)
    except Exception:
        pass
    if args.qa_policy == "strict":
        gate = (feature_meta.get("qa_gate") or "").lower()
        if gate and gate not in {"pass", "ok"}:
            _log_warn(f"[echo_inject]   SKIP: QA gate '{gate}' failed strict policy for {features_path.name}")
            return
    missing_keys = []
    if feature_meta and not feature_meta.get("source_hash"):
        missing_keys.append("source_hash")
    if feature_meta and not feature_meta.get("config_fingerprint"):
        missing_keys.append("config_fingerprint")
    if missing_keys:
        _log_warn(f"[echo_inject]   WARN: feature meta missing {missing_keys} for {features_path}")
    if warn_feature:
        _log_warn(f"[echo_inject]   WARN feature lint ({features_path.name}): {warn_feature}")
    if warn_hci:
        _log_warn(f"[echo_inject]   WARN hci lint ({hci_path.name}): {warn_hci}")

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

    # Persist full neighbor payload for traceability
    neighbors_out = track_dir / f"{track_dir.name}.neighbors.json"
    try:
        write_neighbors_file(str(neighbors_out), echo_data, max_neighbors=None, max_bytes=5 << 20)
        lint_neighbor_warns, _ = lint_json_file(neighbors_out, "neighbors")
        warnings.extend([f"{neighbors_out.name}:{w}" for w in lint_neighbor_warns])
        if not args.quiet:
            warn_suffix = f" (warnings={lint_neighbor_warns})" if lint_neighbor_warns else ""
            _log_info(f"[echo_inject]   Wrote neighbors -> {neighbors_out}{warn_suffix}")
    except Exception as e:  # noqa: BLE001
        _log_warn(f"[echo_inject]   WARN: failed to write neighbors file {neighbors_out}: {e}")

    client_json, inject_warns, bundle = inject_echo_into_client(
        client_json,
        feature_meta,
        hci_meta,
        echo_data,
        neighbors_out,
        max_neighbors_inline=8,
    )
    warnings.extend(inject_warns)
    echo_header_line = bundle["echo_header_line"]
    neighbor_lines = bundle["neighbor_lines"]
    hci_header_lines = build_hci_header_lines(hci_meta, client_json) or []
    audio_header_lines_calc = None
    neighbor_meta_lines = bundle["neighbor_meta_lines"]
    if feature_meta:
        gain_db = feature_meta.get("loudness_normalization_gain_db")
        lufs_raw = feature_meta.get("loudness_LUFS")
        lufs_norm = feature_meta.get("loudness_LUFS_normalized")
        qa = feature_meta.get("qa") or {}
        tempo_conf = feature_meta.get("tempo_confidence")
        tempo_conf_score = feature_meta.get("tempo_confidence_score")
        tempo_conf_score_raw = feature_meta.get("tempo_confidence_score_raw")
        tempo_backend = feature_meta.get("tempo_backend")
        tempo_backend_source = feature_meta.get("tempo_backend_source")
        tempo_backend_detail = feature_meta.get("tempo_backend_detail")
        tempo_backend_meta = feature_meta.get("tempo_backend_meta")
        tempo_alts = feature_meta.get("tempo_alternates")
        tempo_cands = feature_meta.get("tempo_candidates")
        tempo_beats_count = feature_meta.get("tempo_beats_count")
        key_backend = feature_meta.get("key_backend")
        key_conf = feature_meta.get("key_confidence")
        key_conf_raw = feature_meta.get("key_confidence_score_raw")
        key_cands = feature_meta.get("key_candidates")
        feature_fresh = feature_meta.get("feature_freshness")
        audio_fresh = feature_meta.get("audio_feature_freshness")
        sidecar_status = feature_meta.get("sidecar_status")
        sidecar_warnings = feature_meta.get("sidecar_warnings")
        sidecar_line = f"{sidecar_status or 'unknown'} ({tempo_backend_detail or tempo_backend or 'n/a'})"
        if tempo_conf_score is not None:
            sidecar_line += f" | conf={tempo_conf_score}"
        if tempo_alts:
            sidecar_line += f" | alts={tempo_alts}"
        if sidecar_warnings:
            sidecar_line += f" | warnings={sidecar_warnings}"
    audio_header_lines_calc = [
        "# AUDIO_PIPELINE:",
        f"#   normalized_for_features={feature_meta.get('normalized_for_features')}",
        f"#   gain_db={gain_db}",
        f"#   loudness_raw_LUFS={lufs_raw}",
            f"#   loudness_norm_LUFS={lufs_norm}",
            f"#   tempo_primary={feature_meta.get('tempo_primary')}",
            f"#   tempo_alt_half={feature_meta.get('tempo_alt_half')}",
            f"#   tempo_alt_double={feature_meta.get('tempo_alt_double')}",
            f"#   tempo_choice_reason={feature_meta.get('tempo_choice_reason')}",
            f"#   tempo_confidence={tempo_conf}",
            f"#   tempo_confidence_score={tempo_conf_score}",
            f"#   tempo_confidence_score_raw={tempo_conf_score_raw}",
            f"#   tempo_backend={tempo_backend}",
            f"#   tempo_backend_source={tempo_backend_source}",
            f"#   tempo_backend_detail={tempo_backend_detail}",
            f"#   tempo_backend_meta={tempo_backend_meta}",
            f"#   tempo_alternates={tempo_alts}",
            f"#   tempo_candidates={tempo_cands}",
            f"#   tempo_beats_count={tempo_beats_count}",
            f"#   key_backend={key_backend}",
            f"#   key_confidence={key_conf}",
            f"#   key_confidence_score_raw={key_conf_raw}",
            f"#   key_candidates={key_cands}",
            f"#   qa_peak_dbfs={qa.get('peak_dbfs')}",
            f"#   qa_rms_dbfs={qa.get('rms_dbfs')}",
            f"#   qa_clipping={qa.get('clipping')}",
            f"#   qa_silence_ratio={qa.get('silence_ratio')}",
            f"#   qa_status={qa.get('status')}",
            f"#   qa_gate={feature_meta.get('qa_gate')}",
            f"#   cache_status={feature_meta.get('cache_status')}",
            f"#   feature_freshness={feature_fresh}",
            f"#   audio_feature_freshness={audio_fresh}",
            f"#   source_hash={feature_meta.get('source_hash')}",
        f"#   sidecar_status={sidecar_status}",
        f"#   sidecar_warnings={sidecar_warnings}",
        f"#   sidecar_health={sidecar_line}",
    ]
    # Optional audio metadata block
    audio_meta_lines = build_audio_metadata_lines(feature_meta)
    if audio_meta_lines:
        audio_header_lines_calc += [
            "",
            "# ==== AUDIO METADATA (probe) ====",
            *audio_meta_lines,
            "",
        ]

    final_score = hci_meta.get("final_score")
    raw_score = hci_meta.get("raw_score")
    calibrated = hci_meta.get("calibrated_score")
    role = hci_meta.get("hci_role") or "unknown"
    # Rebuild the header so we can inject interpretation + neighbor summary
    # while keeping the existing ordering (and avoiding duplicate blocks).
    marker = "/audio import"
    idx_audio = orig_content.find(marker)
    header_prefix_lines: List[str] = []
    if idx_audio != -1:
        header_text = orig_content[:idx_audio]
        header_prefix_lines = header_text.rstrip("\n").splitlines()
        for i, ln in enumerate(header_prefix_lines):
            if ln.lstrip().startswith("# AUDIO_PIPELINE:"):
                header_prefix_lines = header_prefix_lines[:i]
                break
        # Drop any existing HCI INTERPRETATION block to avoid duplicating it
        filtered: List[str] = []
        skipping = False
        for ln in header_prefix_lines:
            if ln.lstrip().startswith("# ==== HCI INTERPRETATION ===="):
                skipping = True
                continue
            if skipping and ln.lstrip().startswith("# ===================================="):
                skipping = False
                filtered.append(ln)
                continue
            if skipping:
                continue
            filtered.append(ln)
        header_prefix_lines = filtered
        while header_prefix_lines and header_prefix_lines[-1].strip() in {"# ====================================", ""}:
            header_prefix_lines.pop()

    audio_header_lines = audio_header_lines_calc

    # Ensure a consistent top-of-file context block for readability.
    # Strip any existing context lines so we can refresh values each run.
    context_prefixes = (
        "# ==== MUSIC ADVISOR - SONG CONTEXT",
        "# Author:",
        "# Version:",
        "# Generated:",
        "# STRUCTURE_POLICY:",
        "# GOLDILOCKS_POLICY:",
        "# HCI_POLICY:",
        "# CONTEXT:",
        "# HCI_V1_SUMMARY:",
        "# PHILOSOPHY:",
    )
    filtered_header = [
        ln for ln in header_prefix_lines
        if not any(ln.startswith(prefix) for prefix in context_prefixes)
    ]
    header_prefix_lines = build_default_context_header(client_json, hci_meta) + filtered_header

    new_content = rebuild_client_rich_content(
        orig_content=orig_content,
        updated_json=client_json,
        neighbor_lines=neighbor_lines,
        prefix_lines=header_prefix_lines,
        hci_header_lines=hci_header_lines,
        audio_header_lines=audio_header_lines,
        neighbor_meta_lines=neighbor_meta_lines,
    )
    new_content = clean_header_spacing(new_content)

    if args.dry_run:
        _log_info(f"[echo_inject]   DRY RUN: would update {client_path}")
        _log_info(f"[echo_inject]   Summary: {echo_header_line}")
        return warnings

    # Atomic write to avoid partial files
    warn_if_client_schema_sparse(client_path, client_json)
    tmp_path = client_path.with_suffix(client_path.suffix + ".tmp")
    tmp_path.write_text(new_content)
    tmp_path.replace(client_path)
    lint_fn = lint_client_rich_text if _is_client_path(client_path) else lint_client_rich_text
    lint_client_warns = lint_fn(new_content)
    warnings.extend([f"{client_path.name}:{w}" for w in lint_client_warns])
    if not args.quiet:
        warn_suffix = f" (warnings={lint_client_warns})" if lint_client_warns else ""
        _log_info(f"[echo_inject]   Updated {client_path}{warn_suffix}")
        _log_info(f"[echo_inject]   Summary: {echo_header_line}")
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
    _log = di.make_logger("echo_inject", structured=os.getenv("LOG_JSON") == "1", defaults={"tool": "echo_inject"}, redact=redact_flag, secrets=redact_values)
    root = validate_root_dir(args.root, logger=_log_warn)
    if not root:
        raise SystemExit(1)
    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        log_stage_start(_log, "echo_inject_client", root=str(root), quiet=bool(args.quiet))

    client_files = find_client_rich_files(root)
    if not client_files:
        _log_info(f"[echo_inject] No *.{names.CLIENT_TOKEN}.rich.txt files found under {root}")
        return

    def redact(path: Path) -> str:
        return str(path).replace(HOME, "~")

    lint_warn_total = 0
    warnings: list[str] = []
    _log_info(f"[echo_inject] Found {len(client_files)} rich txt files under {redact(root)}")
    for client_path in client_files:
        _log_info(f"[echo_inject] Processing: {redact(client_path)}")
        try:
            file_warns = process_client_rich_file(client_path, args)
            warnings.extend(file_warns)
        except SystemExit as exc:
            lint_warn_total += 1
            if args.strict:
                raise
            _log_warn(f"[echo_inject] strict lint failure ignored (strict disabled): {exc}")
    status = "ok"
    if (lint_warn_total or warnings) and args.strict:
        status = "error"
    if os.getenv("LOG_JSON") == "1":
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        log_stage_end(
            _log,
            "echo_inject_client",
            status=status,
            root=str(root),
            processed=len(client_files),
            lint_failures=lint_warn_total,
            duration_ms=duration_ms,
            warnings=warnings,
        )
    if (lint_warn_total or warnings) and args.strict:
        raise SystemExit("strict mode: lint warnings present")


if __name__ == "__main__":
    raise SystemExit(main())
