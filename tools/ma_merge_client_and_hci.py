#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env, add_log_format_arg, apply_log_format_env, add_preflight_arg, run_preflight_if_requested, di
from ma_audio_engine.adapters import utc_now_iso
from ma_audio_engine.adapters import load_log_settings, load_runtime_settings
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from ma_audio_engine.schemas import dump_json, HCI
from shared.ma_utils import get_configured_logger
from tools.schema_utils import lint_json_file
from ma_audio_engine.schemas import lint_client_rich_text
from tools import names
from tools.key_norms_sidecar import format_key_name

# Optional client-rich schema support; fallback to base structures if not present.
try:  # pragma: no cover - guarded import
    from ma_audio_engine.schemas import CLIENTRich  # type: ignore
except Exception:  # noqa: BLE001
    CLIENTRich = None  # type: ignore

_log = get_configured_logger("ma_merge_client_and_hci")
DEFAULT_TEMPO_LANE_ID = os.environ.get("TEMPO_LANE_ID", "tier1__2015_2024")
DEFAULT_TEMPO_BIN_WIDTH = float(os.environ.get("TEMPO_BIN_WIDTH", "2.0"))
DEFAULT_TEMPO_DB = os.environ.get("TEMPO_DB") or None


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _format_tempo_overlay(payload: Dict[str, Any]) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    lane_id = payload.get("lane_id")
    lane_stats = payload.get("lane_stats") or {}
    song_bin = payload.get("song_bin") or {}
    advisory_text = str(payload.get("advisory_text") or "").strip()
    if not lane_id or not lane_stats or not advisory_text:
        return None

    peak_pct = lane_stats.get("peak_cluster_percent_of_lane") or 0.0
    try:
        peak_pct_val = float(peak_pct)
    except Exception:
        peak_pct_val = 0.0
    peak_pct_str = f"{peak_pct_val * 100:.1f}% of lane"
    peak_range = lane_stats.get("peak_cluster_bpm_range") or []
    hot_zone = "unknown"
    if isinstance(peak_range, (list, tuple)) and len(peak_range) == 2:
        try:
            hot_min = float(peak_range[0])
            hot_max = float(peak_range[1])
            hot_zone = f"{hot_min:.1f}–{hot_max:.1f} BPM"
        except Exception:
            hot_zone = "unknown"
    song_bpm = payload.get("song_bpm")
    lane_median = lane_stats.get("median_bpm")
    hit_count = int(song_bin.get("hit_count") or 0)
    percent = song_bin.get("percent_of_lane") or 0.0
    try:
        pct_val = float(percent)
    except Exception:
        pct_val = 0.0
    pct_str = f"{pct_val * 100:.1f}% of lane"
    try:
        song_bpm_str = f"{float(song_bpm):.1f}"
    except Exception:
        song_bpm_str = "unknown"
    try:
        lane_median_str = f"{float(lane_median):.1f}"
    except Exception:
        lane_median_str = "unknown"
    summary_line = advisory_text.replace("\n", " ").strip()
    if not summary_line:
        return None
    delta = payload.get("suggested_delta_bpm") or []
    delta_line = None
    if isinstance(delta, (list, tuple)) and len(delta) == 2:
        try:
            d_lo, d_hi = sorted([float(delta[0]), float(delta[1])])
            if d_hi < 0:
                delta_line = f"nudge_to_hit_medium: slow down ~{abs(d_hi):.1f}–{abs(d_lo):.1f} BPM"
            elif d_lo > 0:
                delta_line = f"nudge_to_hit_medium: speed up ~{d_lo:.1f}–{d_hi:.1f} BPM"
            else:
                delta_line = f"nudge_to_hit_medium: -{abs(d_lo):.1f} to +{d_hi:.1f} BPM"
        except Exception:
            delta_line = None

    lines = [
        "# TEMPO LANE OVERLAY (BPM)",
        f"# lane_id: {lane_id}",
        f"# song_bpm: {song_bpm_str}",
        f"# lane_median_bpm: {lane_median_str}",
        f"# lane_hot_zone: {hot_zone}",
        f"# hits_at_song_bpm: {hit_count} ({pct_str})",
        f"# lane_hot_zone_share: {peak_pct_str} (historical hit medium)",
    ]
    if delta_line:
        lines.append(f"# {delta_line}")
    lines.append("#")
    lines.extend(
        [
            "# SUMMARY:",
            f"# {summary_line}",
        ]
    )
    return "\n".join(lines)


def load_tempo_overlay_block(audio_name: Optional[str], base_dir: Path) -> Optional[str]:
    """Best-effort load/format tempo overlay block from a sidecar JSON in base_dir."""
    if not audio_name:
        return None
    # Prefer stem (strip extensions) to match pipeline artifacts, fall back to full name.
    stem = Path(audio_name).stem
    sidecar_path = base_dir / f"{stem}{names.tempo_norms_sidecar_suffix()}"
    if not sidecar_path.exists():
        alt = base_dir / f"{audio_name}{names.tempo_norms_sidecar_suffix()}"
        if alt.exists():
            sidecar_path = alt
    if not sidecar_path.exists():
        # Try to build on the fly using features BPM if available
        features_path = base_dir / f"{stem}.features.json"
        if not features_path.exists():
            candidates = list(base_dir.glob(f"{stem}*.features.json"))
            if candidates:
                features_path = candidates[0]
        if features_path.exists():
            try:
                feat = json.loads(features_path.read_text())
                tempo_bpm = feat.get("tempo_bpm")
                if tempo_bpm:
                    from tools import tempo_norms_sidecar as tns  # local import to avoid heavy deps

                    # resolve DB: env override -> default -> tempo_demo fallback
                    if DEFAULT_TEMPO_DB:
                        candidate_db = Path(DEFAULT_TEMPO_DB).expanduser().resolve()
                    else:
                        candidate_db = Path(tns.get_lyric_intel_db_path()).expanduser().resolve()
                    if not candidate_db.exists():
                        _log(f"[WARN] tempo overlay skipped: DB not found at {candidate_db}")
                        return None

                    conn = sqlite3.connect(str(candidate_db))
                    tns.ensure_schema(conn)
                    lane_bpms = tns.load_lane_bpms(conn, DEFAULT_TEMPO_LANE_ID)
                    if lane_bpms:
                        payload = tns.build_sidecar_payload(DEFAULT_TEMPO_LANE_ID, float(tempo_bpm), DEFAULT_TEMPO_BIN_WIDTH, lane_bpms)
                        sidecar_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                        _log(f"[tempo_overlay] built tempo norms sidecar at {sidecar_path} using DB={candidate_db}")
                    else:
                        _log(f"[WARN] tempo overlay skipped: no lane BPMS for lane_id={DEFAULT_TEMPO_LANE_ID} in DB={candidate_db}")
                    conn.close()
            except Exception as exc:  # noqa: BLE001
                _log(f"[WARN] tempo overlay auto-build failed: {exc}")
        if not sidecar_path.exists():
            return None
    try:
        payload = json.loads(sidecar_path.read_text())
    except Exception as exc:  # noqa: BLE001
        _log(f"[WARN] Failed to read tempo norms sidecar {sidecar_path}: {exc}")
        return None
    return _format_tempo_overlay(payload)


def _format_key_overlay(payload: Dict[str, Any]) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    lane_id = payload.get("lane_id")
    song_key = payload.get("song_key") or {}
    lane_stats = payload.get("lane_stats") or {}
    placement = payload.get("song_placement") or {}
    advisory_text = str((payload.get("advisory") or {}).get("advisory_text") or "").strip()
    advisory_meta = payload.get("advisory") or {}
    if not lane_id or not song_key or not advisory_text:
        return None
    primary_family = lane_stats.get("primary_family") or []
    primary_disp = ", ".join(format_key_name(k) for k in primary_family) if primary_family else "n/a"
    full_name = song_key.get("full_name") or f"{song_key.get('root_name', '')} {song_key.get('mode', '')}".strip()
    same_count = placement.get("same_key_count", 0)
    same_pct = placement.get("same_key_percent") or 0.0
    mode_pct = placement.get("same_mode_percent") or 0.0
    try:
        same_pct_val = float(same_pct)
    except Exception:
        same_pct_val = 0.0
    try:
        mode_pct_val = float(mode_pct)
    except Exception:
        mode_pct_val = 0.0
    pct_str = f"{same_pct_val * 100:.1f}% of lane"
    mode_pct_str = f"{mode_pct_val * 100:.1f}% of lane"
    hist_med = lane_stats.get("historical_hit_medium") or []
    hist_med_line = ""
    if hist_med:
        top_hist = hist_med[:3]
        hist_med_line = ", ".join(
            f"{format_key_name(item.get('key_name',''))} ({(item.get('percent') or 0)*100:.1f}%)" for item in top_hist
        )
    neighbors = placement.get("neighbor_keys") or []
    neighbor_line = ""
    if neighbors:
        top_neighbors = neighbors[:2]
        neighbor_line = ", ".join(f"{format_key_name(nb.get('key_name',''))} ({(nb.get('percent') or 0)*100:.1f}%)" for nb in top_neighbors)
    transpositions = advisory_meta.get("suggested_transpositions") or []
    trans_line = ", ".join(f"{'+' if t > 0 else ''}{t}" for t in transpositions) if transpositions else ""
    lane_shape = (lane_stats.get("lane_shape") or {}) if isinstance(lane_stats, dict) else {}
    shape_line = ""
    try:
        ent = float(lane_shape.get("entropy", 0.0))
        flat = float(lane_shape.get("flatness", 0.0))
        ms = lane_shape.get("mode_split") or {}
        maj = ms.get("major_share", 0.0)
        minr = ms.get("minor_share", 0.0)
        shape_line = f"entropy={ent:.2f}, flatness={flat:.2f}, major={maj*100:.1f}%, minor={minr*100:.1f}%"
    except Exception:
        shape_line = ""
    target_moves = advisory_meta.get("target_key_moves") or []
    target_line = ""
    if target_moves:
        grouped: Dict[str, list[str]] = {"relative": [], "parallel": [], "fifth_neighbor": [], "historical_hit_medium": []}
        def _label(reason: str) -> str:
            return {
                "relative": "relative",
                "parallel": "parallel",
                "fifth_neighbor": "fifths",
                "historical_hit_medium": "lane_top",
            }.get(reason, reason or "lane_top")
        for m in target_moves:
            reason = m.get("reason") or "lane_top"
            pct = m.get("lane_percent")
            pct_str = f", {pct*100:.1f}% lane" if isinstance(pct, (int, float)) else ""
            weight = m.get("weight")
            weight_str = f", w={weight:.2f}" if isinstance(weight, (int, float)) else ""
            cdist = m.get("circle_distance")
            cdist_str = f", c5={cdist}" if isinstance(cdist, (int, float)) else ""
            tags = m.get("rationale_tags") or []
            tags_str = f", tags={';'.join(tags)}" if tags else ""
            disp = f"{m.get('target_key','')} ({'+' if m.get('semitone_delta',0)>0 else ''}{m.get('semitone_delta',0)} st{pct_str}{weight_str}{cdist_str}{tags_str})"
            grouped.setdefault(reason, []).append(disp)
        pieces = []
        for key in ("relative", "parallel", "fifth_neighbor", "historical_hit_medium"):
            vals = grouped.get(key) or []
            if vals:
                pieces.append(f"{_label(key)} -> " + ", ".join(vals))
        # include any stray reasons
        for key, vals in grouped.items():
            if key in ("relative", "parallel", "fifth_neighbor", "historical_hit_medium"):
                continue
            if vals:
                pieces.append(f"{_label(key)} -> " + ", ".join(vals))
        target_line = " | ".join(pieces)
    summary_line = advisory_text.replace("\n", " ").strip()
    if not summary_line:
        return None
    mode_top = lane_stats.get("mode_top_keys") or {}
    fifths_chain = lane_stats.get("fifths_chain") or []
    lines = [
        "# KEY LANE OVERLAY (KEY)",
        f"# lane_id: {lane_id}",
        f"# song_key: {full_name}",
        "# legend: st=semitones delta; w=weight; c5=circle-of-fifths distance; tags=rationale tags",
        f"# primary_key_family: {primary_disp}",
        f"# songs_in_same_key: {same_count} ({pct_str})",
        f"# songs_in_same_mode: {mode_pct_str}",
    ]
    if shape_line:
        lines.append(f"# lane_shape: {shape_line}")
    if mode_top:
        major_top = mode_top.get("major") or []
        minor_top = mode_top.get("minor") or []
        if major_top:
            lines.append(f"# mode_top_major: {', '.join(major_top)}")
        if minor_top:
            lines.append(f"# mode_top_minor: {', '.join(minor_top)}")
    if fifths_chain:
        lines.append(f"# fifths_chain: {', '.join(fifths_chain)}")
    if hist_med_line:
        lines.append(f"# historical_hit_medium: {hist_med_line}")
    if neighbor_line:
        lines.append(f"# neighbor_pockets: {neighbor_line}")
    if trans_line:
        lines.append(f"# suggested_transpose_semitones: {trans_line}")
    if target_line:
        lines.append(f"# target_keys_from_hits: {target_line}")
    lines += [
        "#",
        "# SUMMARY:",
        f"# {summary_line}",
    ]
    return "\n".join(lines)


def load_key_overlay_block(audio_name: Optional[str], base_dir: Path) -> Optional[str]:
    if not audio_name:
        return None
    sidecar_path = base_dir / f"{audio_name}{names.key_norms_sidecar_suffix()}"
    if not sidecar_path.exists():
        return None
    try:
        payload = json.loads(sidecar_path.read_text())
    except Exception as exc:  # noqa: BLE001
        _log(f"[WARN] Failed to read key norms sidecar {sidecar_path}: {exc}")
        return None
    return _format_key_overlay(payload)


def _enrich_from_disk(client_path: Path, client_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    If the client pack is missing pipeline/echo metadata, try to hydrate it from sibling files
    in the same output directory (features.json / neighbors.json).
    """
    base_dir = client_path.parent
    # Feature pipeline enrichment
    fpm = client_data.get("feature_pipeline_meta") or {}
    needs_pipeline = not fpm or len(fpm.keys()) <= 3
    feature_file = None
    if needs_pipeline:
        candidates = sorted(base_dir.glob("*features.json"))
        if candidates:
            feature_file = candidates[-1]
    if feature_file:
        try:
            feat = json.loads(feature_file.read_text())
            qa_block = feat.get("qa") or {}
            keys = [
                "normalized_for_features",
                "loudness_normalization_gain_db",
                "loudness_LUFS",
                "loudness_LUFS_normalized",
                "tempo_primary",
                "tempo_alt_half",
                "tempo_alt_double",
                "tempo_choice_reason",
                "tempo_confidence",
                "tempo_confidence_score",
                "tempo_confidence_score_raw",
                "tempo_backend",
                "tempo_backend_source",
                "tempo_backend_detail",
                "tempo_backend_meta",
                "tempo_alternates",
                "tempo_candidates",
                "tempo_beats_count",
                "key_backend",
                "key_confidence",
                "key_confidence_score_raw",
                "key_candidates",
                "qa_peak_dbfs",
                "qa_rms_dbfs",
                "qa_clipping",
                "qa_silence_ratio",
                "qa_status",
                "qa_gate",
                "cache_status",
                "feature_freshness",
                "audio_feature_freshness",
                "source_hash",
                "sidecar_status",
                "sidecar_warnings",
                "sidecar_health",
            ]
            hydrated = {k: feat.get(k) for k in keys if k in feat}
            # QA lives nested in some files.
            for k_nested, k_out in [
                ("peak_dbfs", "qa_peak_dbfs"),
                ("rms_dbfs", "qa_rms_dbfs"),
                ("clipping", "qa_clipping"),
                ("silence_ratio", "qa_silence_ratio"),
                ("status", "qa_status"),
                ("gate", "qa_gate"),
            ]:
                if k_nested in qa_block:
                    hydrated[k_out] = qa_block.get(k_nested)
            if "sidecar_health" not in hydrated:
                # Compose a lightweight health string if we have meta.
                backend = feat.get("tempo_backend_detail")
                conf = feat.get("tempo_confidence_score")
                alts = feat.get("tempo_alternates")
                if backend or conf or alts:
                    hydrated["sidecar_health"] = f"used ({backend or 'external'}) | conf={conf} | alts={alts}"

            # Preserve existing non-null values
            merged = dict(hydrated)
            merged.update({k: v for k, v in fpm.items() if v not in (None, "")})
            merged.setdefault("feature_freshness", "ok")
            merged.setdefault("audio_feature_freshness", "ok")
            client_data["feature_pipeline_meta"] = merged
        except Exception:
            pass

    # Echo enrichment
    needs_echo = not client_data.get("historical_echo_meta") or not client_data.get("historical_echo_v1")
    neighbors_file = (base_dir / f"{client_path.stem.replace('.client', '')}.neighbors.json").resolve()
    if needs_echo and neighbors_file.exists():
        try:
            neigh = json.loads(neighbors_file.read_text())
            neighbors = neigh.get("neighbors") or []
            neighbor_tiers = sorted({n.get("tier") for n in neighbors if n.get("tier")})
            decade_counts = neigh.get("decade_counts") or {}
            primary_decade = None
            if decade_counts:
                primary_decade = max(decade_counts.items(), key=lambda kv: kv[1])[0]
            client_data["historical_echo_meta"] = {
                "neighbors_file": str(neighbors_file),
                "neighbors_total": len(neighbors),
                "neighbor_tiers": neighbor_tiers,
                "neighbors_kept_inline": min(4, len(neighbors)),
                "primary_decade": primary_decade,
            }
            neigh.setdefault("primary_decade", primary_decade)
            client_data["historical_echo_v1"] = neigh
        except Exception:
            pass

    return client_data


def _extract_hci_values(hci_data: Dict[str, Any]) -> Tuple[float, float, float, str]:
    """
    Extract (raw, calibrated, final, role) from a .hci.json dict,
    tolerating slightly different schemas and missing fields.
    """
    # --- RAW ---
    raw = None
    if "HCI_v1_score_raw" in hci_data:
        try:
            raw = float(hci_data["HCI_v1_score_raw"])
        except Exception:
            raw = None

    hci_block = hci_data.get("HCI_v1") or {}
    if raw is None and isinstance(hci_block, dict):
        for key in ("raw", "HCI_v1_score_raw", "HCI_v1_score"):
            if key in hci_block:
                try:
                    raw = float(hci_block[key])
                    break
                except Exception:
                    pass

    if raw is None:
        raw = 0.0

    # --- CALIBRATED SCORE (pre-final) ---
    calibrated = None
    if "HCI_v1_score" in hci_data:
        try:
            calibrated = float(hci_data["HCI_v1_score"])
        except Exception:
            calibrated = None

    if calibrated is None and isinstance(hci_block, dict):
        for key in ("score", "HCI_v1_score"):
            if key in hci_block:
                try:
                    calibrated = float(hci_block[key])
                    break
                except Exception:
                    pass

    if calibrated is None:
        calibrated = raw

    # --- FINAL SCORE (canonical) ---
    final = None
    if "HCI_v1_final_score" in hci_data:
        try:
            final = float(hci_data["HCI_v1_final_score"])
        except Exception:
            final = None

    if final is None and isinstance(hci_block, dict) and "final_score" in hci_block:
        try:
            final = float(hci_block["final_score"])
        except Exception:
            final = None

    # If there is still no final score, fall back to calibrated
    if final is None:
        final = calibrated

    # --- ROLE ---
    role = str(hci_data.get("HCI_v1_role", "unknown"))

    return float(raw), float(calibrated), float(final), role


def _merge_hci_into_pack(
    client_data: Dict[str, Any],
    hci_data: Dict[str, Any],
    raw: float,
    calibrated: float,
    final: float,
    role: str,
) -> Dict[str, Any]:
    """
    Attach HCI info into the client JSON pack:
      - top-level canonical fields
      - nested HCI_v1 block kept in sync
    """
    # Top-level canonical fields
    client_data["HCI_v1_score_raw"] = round(raw, 3)
    client_data["HCI_v1_score"] = round(calibrated, 3)
    client_data["HCI_v1_final_score"] = round(final, 3)
    client_data["HCI_v1_role"] = role

    # Nested block, if present
    hci_block = hci_data.get("HCI_v1")
    if not isinstance(hci_block, dict):
        hci_block = {}

    hci_block["raw"] = round(raw, 3)
    hci_block["score"] = round(calibrated, 3)
    hci_block["final_score"] = round(final, 3)

    meta = hci_block.get("meta")
    if not isinstance(meta, dict):
        meta = {}

    # Keep any calibration meta if present
    cal_meta = meta.get("calibration")
    if not isinstance(cal_meta, dict) and "HCI_v1" in hci_data:
        cal_meta = hci_data["HCI_v1"].get("meta", {}).get("calibration")

    if isinstance(cal_meta, dict):
        meta["calibration"] = cal_meta

    meta.setdefault("role", role)
    hci_block["meta"] = meta

    client_data["HCI_v1"] = hci_block

    return client_data


def _build_rich_text(
    client_data: Dict[str, Any],
    raw: float,
    calibrated: float,
    final: float,
    role: str,
    tempo_overlay_block: Optional[str] = None,
    key_overlay_block: Optional[str] = None,
) -> str:
    audio_name = str(client_data.get("audio_name", "UNKNOWN_AUDIO"))
    region = str(client_data.get("region", "US"))
    profile = str(client_data.get("profile", "Pop"))
    now = utc_now_iso()

    # Pull pipeline/meta blocks if present.
    fpm = client_data.get("feature_pipeline_meta") or {}
    echo_meta = client_data.get("historical_echo_meta") or {}
    echo_v1 = client_data.get("historical_echo_v1") or {}
    neighbors = echo_v1.get("neighbors") or []
    ttc_block = client_data.get("ttc") or {}
    ttc_sec = (
        ttc_block.get("ttc_seconds_first_chorus")
        or client_data.get("ttc_seconds_first_chorus")
        or client_data.get("features", {}).get("ttc_seconds_first_chorus")
    )
    ttc_bars = (
        ttc_block.get("ttc_bars_first_chorus")
        or client_data.get("ttc_bars_first_chorus")
        or client_data.get("features", {}).get("ttc_bars_first_chorus")
    )
    ttc_source = ttc_block.get("ttc_source") or client_data.get("ttc_source")
    ttc_method = ttc_block.get("ttc_estimation_method") or client_data.get("ttc_estimation_method")

    SEP = "# ===================================="

    def fmt_bool(val: Any) -> str:
        if isinstance(val, bool):
            return "True" if val else "False"
        return "unknown"

    def fmt_val(val: Any) -> str:
        if val is None:
            return "None"
        return str(val)

    header_lines = [
        "# ==== MUSIC ADVISOR - SONG CONTEXT ====",
        f"# Author: Keith Hetrick - injects HCI+Echo context into .{names.CLIENT_TOKEN}.rich.txt",
        "# Version: HCI+Echo context v1.1",
        f"# Generated: {now}",
        SEP,
        "# STRUCTURE_POLICY: mode=optional | reliable=false | use_ttc=false | use_exposures=false",
        "# GOLDILOCKS_POLICY: active=true | priors={'Market': 0.5, 'Emotional': 0.5} | caps={'Market': 0.58, 'Emotional': 0.58}",
        "# HCI_POLICY: HCI_v1_final_score is canonical; raw/calibrated are provided for transparency only.",
        "# CONTEXT EXAMPLES: 'Blinding Lights' (most-streamed hit) can land mid-scale on HCI_v1; 'Flowers' can land high — HCI_v1 reflects historical-echo shape, not popularity.",
        f"# CONTEXT: region={region}, profile={profile}, audio_name={audio_name}",
        f"# HCI_V1_SUMMARY: final={final:.3f} | role={role} | raw={raw if raw is not None else 'unknown'} | calibrated={calibrated if calibrated is not None else 'unknown'}",
        "#",
        SEP,
        "# AUDIO_PIPELINE:",
        f"#   normalized_for_features={fmt_bool(fpm.get('normalized_for_features'))}",
        f"#   gain_db={fmt_val(fpm.get('loudness_normalization_gain_db', 'unknown'))}",
        f"#   loudness_raw_LUFS={fmt_val(fpm.get('loudness_LUFS', 'unknown'))}",
        f"#   loudness_norm_LUFS={fmt_val(fpm.get('loudness_LUFS_normalized', 'unknown'))}",
        f"#   tempo_primary={fmt_val(fpm.get('tempo_primary', 'unknown'))}",
        f"#   tempo_alt_half={fmt_val(fpm.get('tempo_alt_half', 'unknown'))}",
        f"#   tempo_alt_double={fmt_val(fpm.get('tempo_alt_double', 'unknown'))}",
        f"#   tempo_choice_reason={fmt_val(fpm.get('tempo_choice_reason', 'unknown'))}",
        f"#   tempo_confidence={fmt_val(fpm.get('tempo_confidence', 'unknown'))}",
        f"#   tempo_confidence_score={fmt_val(fpm.get('tempo_confidence_score', 'unknown'))}",
        f"#   tempo_confidence_score_raw={fmt_val(fpm.get('tempo_confidence_score_raw', 'unknown'))}",
        f"#   tempo_backend={fmt_val(fpm.get('tempo_backend', 'unknown'))}",
        f"#   tempo_backend_source={fmt_val(fpm.get('tempo_backend_source', 'unknown'))}",
        f"#   tempo_backend_detail={fmt_val(fpm.get('tempo_backend_detail', 'unknown'))}",
        f"#   tempo_backend_meta={fmt_val(fpm.get('tempo_backend_meta', 'unknown'))}",
        f"#   tempo_alternates={fmt_val(fpm.get('tempo_alternates', 'unknown'))}",
        f"#   tempo_candidates={fmt_val(fpm.get('tempo_candidates', 'unknown'))}",
        f"#   tempo_beats_count={fmt_val(fpm.get('tempo_beats_count', 'unknown'))}",
        f"#   key_backend={fmt_val(fpm.get('key_backend', 'unknown'))}",
        f"#   key_confidence={fmt_val(fpm.get('key_confidence', 'unknown'))}",
        f"#   key_confidence_score_raw={fmt_val(fpm.get('key_confidence_score_raw', 'unknown'))}",
        f"#   key_candidates={fmt_val(fpm.get('key_candidates', 'None'))}",
        f"#   qa_peak_dbfs={fmt_val(fpm.get('qa_peak_dbfs', 'unknown'))}",
        f"#   qa_rms_dbfs={fmt_val(fpm.get('qa_rms_dbfs', 'unknown'))}",
        f"#   qa_clipping={fmt_val(fpm.get('qa_clipping', 'unknown'))}",
        f"#   qa_silence_ratio={fmt_val(fpm.get('qa_silence_ratio', 'unknown'))}",
        f"#   qa_status={fmt_val(fpm.get('qa_status', 'unknown'))}",
        f"#   qa_gate={fmt_val(fpm.get('qa_gate', 'unknown'))}",
        f"#   cache_status={fmt_val(fpm.get('cache_status', 'unknown'))}",
        f"#   feature_freshness={fmt_val(fpm.get('feature_freshness', 'unknown'))}",
        f"#   audio_feature_freshness={fmt_val(fpm.get('audio_feature_freshness', 'unknown'))}",
        f"#   source_hash={fmt_val(fpm.get('source_hash', 'unknown'))}",
        f"#   sidecar_status={fmt_val(fpm.get('sidecar_status', 'unknown'))}",
        f"#   sidecar_warnings={fmt_val(fpm.get('sidecar_warnings', 'None'))}",
        f"#   sidecar_health={fmt_val(fpm.get('sidecar_health', 'unknown'))}",
        "#",
        "# TTC:",
        f"#   ttc_seconds_first_chorus={fmt_val(ttc_sec)}",
        f"#   ttc_bars_first_chorus={fmt_val(ttc_bars)}",
        f"#   ttc_source={fmt_val(ttc_source)}",
        f"#   ttc_method={fmt_val(ttc_method)}",
        "#",
    ]

    if tempo_overlay_block:
        header_lines.append("#")
        header_lines.extend(tempo_overlay_block.splitlines())
        header_lines.append("")

    if key_overlay_block:
        header_lines.append("#")
        header_lines.extend(key_overlay_block.splitlines())
        header_lines.append("")

    header_lines.extend(
        [
            SEP,
            "# NEIGHBOR_META:",
            f"#   neighbors_total={fmt_val(echo_meta.get('neighbors_total', 'unknown'))}",
            f"#   neighbor_tiers={fmt_val(echo_meta.get('neighbor_tiers', 'unknown'))}",
            f"#   neighbors_kept_inline={fmt_val(echo_meta.get('neighbors_kept_inline', 'unknown'))}",
            f"#   neighbors_file={fmt_val(echo_meta.get('neighbors_file', 'unknown'))}",
        ]
    )

    # Echo summary
    primary_decade = echo_v1.get("primary_decade") or echo_meta.get("primary_decade") or "unknown"
    decade_counts = (echo_v1.get("decade_counts") if isinstance(echo_v1, dict) else None) or {}
    primary_count = None
    if isinstance(decade_counts, dict) and primary_decade in decade_counts:
        primary_count = decade_counts[primary_decade]
    top_neighbor = None
    if neighbors:
        top_neighbor = neighbors[0]
    top_summary = ""
    if top_neighbor:
        top_summary = (
            f"{top_neighbor.get('year', 'unknown')} – "
            f"{top_neighbor.get('artist', 'unknown')} — "
            f"{top_neighbor.get('title', 'unknown')} "
            f"(dist={top_neighbor.get('distance', 'unknown')})"
        )

    header_lines.extend(
        [
            "#",
            SEP,
            "# HISTORICAL ECHO V1",
            "# NEIGHBORS",
        ]
    )

    # List up to 4 neighbors
    for idx, n in enumerate(neighbors[:4], start=1):
        tier_raw = n.get("tier", "tier?")
        tier_disp = tier_raw
        if isinstance(tier_raw, str) and tier_raw.startswith("tier1_modern"):
            tier_disp = "tier1_mode"
        header_lines.append(
            f"#   {idx}  {tier_disp:<10} {n.get('distance', 'unk')}  {n.get('year', 'unk')}  {n.get('artist', ''):<20} {n.get('title', ''):<30}"
        )
    header_lines.append(SEP)
    header_lines.append("")

    body = "/audio import " + json.dumps(client_data, indent=2)
    return "\n".join(header_lines) + "\n" + body + "\n"


def merge_client_hci(
    client_data: Dict[str, Any],
    hci_data: Dict[str, Any],
    tempo_overlay_block: Optional[str] = None,
    key_overlay_block: Optional[str] = None,
) -> Tuple[Dict[str, Any], str, list[str], Tuple[float, float, float, str]]:
    """Pure merge helper: returns updated client data, rich_text, lint warnings, and score tuple."""
    warns: list[str] = []
    raw, calibrated, final, role = _extract_hci_values(hci_data)
    client_merged = _merge_hci_into_pack(dict(client_data), hci_data, raw, calibrated, final, role)
    rich_text = _build_rich_text(
        client_merged,
        raw,
        calibrated,
        final,
        role,
        tempo_overlay_block=tempo_overlay_block,
        key_overlay_block=key_overlay_block,
    )
    rich_warns = lint_client_rich_text(rich_text)
    warns.extend(rich_warns)
    return client_merged, rich_text, warns, (raw, calibrated, final, role)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=f"Merge client JSON and HCI JSON into a rich {names.CLIENT_TOKEN} pack."
    )
    ap.add_argument(
        "--client-json",
        required=False,
        help=f"Path to the base {names.CLIENT_TOKEN} JSON pack (from pack_writer / Automator #1).",
    )
    ap.add_argument(
        "--hci",
        required=True,
        help="Path to the .hci.json file with HCI_v1_* scores.",
    )
    ap.add_argument(
        "--out",
        required=False,
        help=f"Output path for the .{names.CLIENT_TOKEN}.rich.txt file.",
    )
    ap.add_argument(
        "--client-out",
        required=False,
        help=f"Output path for the .{names.CLIENT_TOKEN}.rich.txt file.",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on lint/schema warnings for inputs/outputs.",
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
    add_log_format_arg(ap)
    add_preflight_arg(ap)

    args = ap.parse_args()
    apply_log_sandbox_env(args)
    apply_log_format_env(args)
    run_preflight_if_requested(args)
    # Normalize runtime/config defaults across CLIs.
    _ = load_runtime_settings(args)

    log_settings = load_log_settings(args)
    global _log
    _log = get_configured_logger("ma_merge_client_and_hci", defaults={"tool": "ma_merge_client_and_hci"})

    if not args.client_json:
        raise SystemExit("The --client-json path is required.")
    client_path = Path(args.client_json).resolve()
    hci_path = Path(args.hci).resolve()
    chosen_out = args.client_out or args.out
    if not chosen_out:
        # Default to client suffix based on input name.
        suffix = names.client_rich_suffix()
        chosen_out = str(client_path.with_suffix(suffix))
    out_path = Path(chosen_out).resolve()

    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        _log("start", {"event": "start", "tool": "ma_merge_client_and_hci", "client": str(client_path), "hci": str(hci_path), "out": str(out_path)})
        log_stage_start(
            _log,
            "merge_client_hci",
            client=str(client_path),
            hci=str(hci_path),
            out=str(out_path),
        )

    client_data = _load_json(client_path)
    client_data = _enrich_from_disk(client_path, client_data)
    # Use raw JSON to preserve any auxiliary keys written by upstream tools.
    # The schema object drops unknown fields, which caused raw/calibrated scores
    # to be lost and rendered as 0.000 in the rich text header.
    hci_data = json.loads(hci_path.read_text())
    tempo_overlay_block = load_tempo_overlay_block(client_data.get("audio_name"), out_path.parent)
    key_overlay_block = load_key_overlay_block(client_data.get("audio_name"), out_path.parent)

    warns: list[str] = []
    client_warns, _ = lint_json_file(client_path, "pack")
    hci_warns, _ = lint_json_file(hci_path, "hci")
    warns.extend(client_warns)
    warns.extend(hci_warns)

    client_data, rich_text, merge_warns, scores = merge_client_hci(
        client_data,
        hci_data,
        tempo_overlay_block=tempo_overlay_block,
        key_overlay_block=key_overlay_block,
    )
    raw, calibrated, final, role = scores
    warns.extend(merge_warns)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rich_text)

    rich_warns = lint_client_rich_text(rich_text)
    warns.extend(rich_warns)

    status = "ok"
    if warns:
        _log(f"[ma_merge_client_and_hci] lint warnings: {warns}")
        status = "error" if args.strict else "ok"

    label = names.CLIENT_TOKEN
    _log(f"[ma_merge_client_and_hci] Wrote {label} rich pack to {out_path}")
    _log(
        "[ma_merge_client_and_hci] "
        f"HCI_v1_final_score={final:.3f}, role={role}, generated={utc_now_iso(timespec='seconds')}"
    )
    if os.getenv("LOG_JSON") == "1":
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        log_stage_end(
            _log,
            "merge_client_hci",
            status=status,
            out=str(out_path),
            duration_ms=duration_ms,
            warnings=warns,
        )
        _log("end", {"event": "end", "tool": "ma_merge_client_and_hci", "out": str(out_path), "status": status, "duration_ms": duration_ms, "warnings": warns})

    if status == "error":
        raise SystemExit("strict mode: lint warnings present")


if __name__ == "__main__":
    main()
