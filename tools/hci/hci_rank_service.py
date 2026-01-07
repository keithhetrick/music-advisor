from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from ma_audio_engine.adapters import is_backend_enabled, list_supported_backends, load_json_guarded, utc_now_iso
from shared.ma_utils.schema_utils import lint_json_file


def load_hci_score(path: Path, logger: Callable[[str], None]) -> Optional[Dict[str, Any]]:
    """Parse a .hci.json and return a flat dict of rank-relevant fields."""
    data = load_json_guarded(path, expect_mapping=True, logger=logger)
    if data is None:
        logger(f"[hci_rank] WARN: failed to parse {path.name}")
        return None
    lint_warnings, _ = lint_json_file(path, kind="hci")
    if lint_warnings:
        logger(f"[hci_rank] WARN lint ({path.name}): {lint_warnings}")
    score = data.get("HCI_v1_final_score") or data.get("HCI_v1_score")
    try:
        score_val = float(score)
    except (TypeError, ValueError):
        return None
    feature_meta = data.get("feature_pipeline_meta") or {}
    qa_meta = feature_meta.get("qa") or {}
    qa_gate = feature_meta.get("qa_gate") or qa_meta.get("gate") or qa_meta.get("status")
    return {
        "path": path,
        "score": score_val,
        "final_tier": data.get("HCI_v1_final_tier"),
        "title": path.stem.replace(".hci", "") if path.stem.endswith(".hci") else path.stem,
        "raw": data.get("HCI_v1_score_raw"),
        "qa_gate": qa_gate,
        "cache_status": feature_meta.get("cache_status"),
        "config_fingerprint": feature_meta.get("config_fingerprint"),
        "pipeline_version": feature_meta.get("pipeline_version"),
        "feature_freshness": feature_meta.get("feature_freshness"),
        "audio_feature_freshness": feature_meta.get("audio_feature_freshness"),
        "sidecar_status": feature_meta.get("sidecar_status"),
        "sidecar_warnings": feature_meta.get("sidecar_warnings"),
        "tempo_backend_detail": feature_meta.get("tempo_backend_detail"),
        "tempo_confidence_score": feature_meta.get("tempo_confidence_score"),
        "historical_echo_meta": data.get("historical_echo_meta"),
    }


def truncate_title(title: str, width: Optional[int]) -> str:
    if width is None or width <= 3 or len(title) <= width:
        return title
    return title[: width - 1] + "…"


def effective_score(entry: Dict[str, Any]) -> float:
    return float(entry.get("score_effective", entry["score"]))


@dataclass
class RankOptions:
    qa_policy_name: str = "default"
    qa_penalty: float = 0.0
    unknown_qa: str = "warn"
    require_sidecar_backend: str = "any"  # or "essentia_madmom"
    require_neighbors_file: bool = False
    tiers_filter: Optional[Sequence[str]] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    top: int = 10
    title_width: Optional[int] = None
    show_sidecar_meta: bool = False
    summarize_qa: bool = False
    fail_on_config_drift: bool = False


def filter_entries(entries: Iterable[Dict[str, Any]], opts: RankOptions, log_warn: Callable[[str], None]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    supported_backends = list_supported_backends()
    qa_counts: Dict[str, int] = {}
    cache_counts: Dict[str, int] = {}
    config_set = set()
    pipeline_versions = set()
    freshness_counts: Dict[str, int] = {}
    audio_fresh_counts: Dict[str, int] = {}
    sidecar_counts: Dict[str, int] = {}
    sidecar_backend_counts: Dict[str, int] = {}
    sidecar_warn_counts: Dict[str, int] = {}

    filtered: List[Dict[str, Any]] = []
    for e in entries:
        gate_raw = e.get("qa_gate")
        gate = (gate_raw or "").lower()
        if gate in ("", "unknown", None):
            if opts.unknown_qa == "drop":
                continue
            if opts.unknown_qa == "warn":
                gate = "unknown"
            else:
                gate = "pass"
        if opts.qa_policy_name == "strict" and gate not in ("pass", "ok"):
            continue

        score_eff = e["score"]
        penalty_applied = False
        if opts.qa_penalty > 0 and gate not in ("", "pass", "ok"):
            score_eff = e["score"] / (1.0 + opts.qa_penalty)
            penalty_applied = True

        if opts.require_sidecar_backend == "essentia_madmom":
            if e.get("sidecar_status") != "used" or e.get("tempo_backend_detail") not in ("essentia", "madmom"):
                continue
        if opts.require_neighbors_file:
            meta_block = e.get("historical_echo_meta") or {}
            if not meta_block.get("neighbors_file") or not meta_block.get("neighbors_total"):
                continue

        e = dict(e)
        e["score_effective"] = score_eff
        e["qa_penalty_applied"] = penalty_applied
        filtered.append(e)

        qa_counts[gate or "unknown"] = qa_counts.get(gate or "unknown", 0) + 1
        cache_counts[e.get("cache_status") or "unknown"] = cache_counts.get(e.get("cache_status") or "unknown", 0) + 1
        if e.get("config_fingerprint"):
            config_set.add(e["config_fingerprint"])
        if e.get("pipeline_version"):
            pipeline_versions.add(e["pipeline_version"])
        freshness = e.get("feature_freshness") or "unknown"
        audio_fresh = e.get("audio_feature_freshness") or "unknown"
        freshness_counts[freshness] = freshness_counts.get(freshness, 0) + 1
        audio_fresh_counts[audio_fresh] = audio_fresh_counts.get(audio_fresh, 0) + 1
        sidecar = e.get("sidecar_status") or "unknown"
        sidecar_counts[sidecar] = sidecar_counts.get(sidecar, 0) + 1
        backend = e.get("tempo_backend_detail") or "unknown"
        sidecar_backend_counts[backend] = sidecar_backend_counts.get(backend, 0) + 1
        if backend not in ("unknown", None):
            if backend not in supported_backends:
                log_warn(f"[hci_rank] WARN: tempo backend '{backend}' not in registry {supported_backends}")
            elif not is_backend_enabled(backend):
                log_warn(f"[hci_rank] WARN: tempo backend '{backend}' is disabled in registry")
        warns = e.get("sidecar_warnings")
        if isinstance(warns, list):
            for w in warns:
                sidecar_warn_counts[w or "unspecified"] = sidecar_warn_counts.get(w or "unspecified", 0) + 1
        elif warns:
            sidecar_warn_counts[str(warns)] = sidecar_warn_counts.get(str(warns), 0) + 1

    meta = {
        "qa_counts": qa_counts,
        "cache_counts": cache_counts,
        "config_set": config_set,
        "pipeline_versions": pipeline_versions,
        "freshness_counts": freshness_counts,
        "audio_fresh_counts": audio_fresh_counts,
        "sidecar_counts": sidecar_counts,
        "sidecar_backend_counts": sidecar_backend_counts,
        "sidecar_warn_counts": sidecar_warn_counts,
    }
    return filtered, meta


def render_report(
    roots: Sequence[Path],
    entries: List[Dict[str, Any]],
    opts: RankOptions,
    meta: Dict[str, Any],
) -> Tuple[int, List[str], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not entries:
        return 0, ["No valid *.hci.json scores found.", ""], [], [], []

    if opts.tiers_filter:
        tiers = {t.strip() for t in opts.tiers_filter if t.strip()}
        entries = [e for e in entries if (e.get("final_tier") in tiers)]

    if opts.min_score is not None:
        entries = [e for e in entries if e["score"] >= opts.min_score]
    if opts.max_score is not None:
        entries = [e for e in entries if e["score"] <= opts.max_score]

    entries.sort(key=lambda x: effective_score(x), reverse=True)
    top_n = entries[: opts.top]
    bottom_n = entries[-opts.top :] if len(entries) > opts.top else entries

    scores_eff = [effective_score(e) for e in entries]
    max_score = max(scores_eff) if scores_eff else None
    min_score = min(scores_eff) if scores_eff else None
    median = None
    if scores_eff:
        sorted_scores_eff = sorted(scores_eff)
        n = len(sorted_scores_eff)
        mid = n // 2
        median = (sorted_scores_eff[mid - 1] + sorted_scores_eff[mid]) / 2 if n % 2 == 0 else sorted_scores_eff[mid]

    lines: List[str] = []
    lines.append("# ==== HCI_v1 Ranking Report ====")
    lines.append(f"# Roots: {', '.join(str(r) for r in roots)}")
    lines.append(f"# Generated: {utc_now_iso(timespec='seconds')}")
    lines.append(f"# Total tracks: {len(entries)}")
    lines.append("# Legend: score = HCI_v1_final_score (audio-based historical echo); higher = closer to long-run US Pop archetypes; tier is the qualitative label.")
    lines.append(f"# Filtered tiers: {','.join(sorted(opts.tiers_filter)) if opts.tiers_filter else 'all'}")
    lines.append(f"# QA: policy={opts.qa_policy_name} | penalty_factor={opts.qa_penalty}")
    if scores_eff:
        lines.append(f"# Stats: max={max_score:.3f} | min={min_score:.3f} | median={median:.3f}")
    if entries:
        tier_counts: Dict[str, int] = {}
        for e in entries:
            tier = e.get("final_tier") or "unknown"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        counts_str = ", ".join(f"{k}: {v}" for k, v in sorted(tier_counts.items()))
        lines.append(f"# Tier counts: {counts_str}")
    if opts.summarize_qa:
        lines.append(f"# QA gates: {dict(sorted(meta['qa_counts'].items()))}")
        lines.append(f"# Cache status: {dict(sorted(meta['cache_counts'].items()))}")
        lines.append(f"# Sidecar status: {dict(sorted(meta['sidecar_counts'].items()))}")
        lines.append(f"# Sidecar backends: {dict(sorted(meta['sidecar_backend_counts'].items()))}")
        if meta["sidecar_warn_counts"]:
            lines.append(f"# Sidecar warnings: {dict(sorted(meta['sidecar_warn_counts'].items()))}")
        if meta["config_set"]:
            lines.append(f"# Config fingerprints ({len(meta['config_set'])}): {sorted(meta['config_set'])}")
        if meta["pipeline_versions"]:
            lines.append(f"# Pipeline versions ({len(meta['pipeline_versions'])}): {sorted(meta['pipeline_versions'])}")
        lines.append(f"# Feature freshness: {dict(sorted(meta['freshness_counts'].items()))}")
        lines.append(f"# Audio vs feature freshness: {dict(sorted(meta['audio_fresh_counts'].items()))}")
        if len(meta["config_set"]) > 1:
            lines.append("# WARNING: multiple config_fingerprint values detected; mixed extractor settings in this batch.")
        if opts.fail_on_config_drift and (len(meta["config_set"]) > 1 or len(meta["pipeline_versions"]) > 1):
            lines.append("# ERROR: config drift detected and --fail-on-config-drift is set; aborting.")
            return 1, lines + ["", ""], entries, top_n, bottom_n
    lines.append("")

    def _fmt_table(title: str, rows: List[Dict[str, Any]], include_raw: bool, full_neighbor_meta: bool = False) -> List[str]:
        out: List[str] = []
        out.append(title)
        out.append(
            f"{'rank':>4}  {'score':>6}  {'raw':>6}  {'tier':<30}  title"
            if include_raw
            else f"{'rank':>4}  {'score':>6}  title"
        )
        out.append("-" * 72)
        for i, e in enumerate(rows, 1):
            score_disp = effective_score(e)
            raw = e.get("raw")
            raw_str = f"{raw:.3f}" if isinstance(raw, (int, float)) else "n/a"
            suffix = ""
            sidecar = e.get("sidecar_status") or "unknown"
            backend = e.get("tempo_backend_detail") or "unknown"
            conf = e.get("tempo_confidence_score")
            if opts.show_sidecar_meta:
                conf_str = f"{conf:.2f}" if isinstance(conf, (int, float)) else "n/a"
                suffix = f"  [sidecar={sidecar}/{backend}, conf={conf_str}]"
            elif sidecar != "used" or backend not in ("essentia", "madmom"):
                suffix = f"  [sidecar={sidecar}/{backend}]"
            neighbor_meta = ""
            if full_neighbor_meta:
                meta_block = e.get("historical_echo_meta") or {}
                if meta_block:
                    neighbor_meta = (
                        f" [neighbors={meta_block.get('neighbors_total','?')}/{meta_block.get('neighbors_kept_inline','?')} "
                        f"tiers={meta_block.get('neighbor_tiers','?')}]"
                    )
            if include_raw:
                out.append(
                    f"{i:>4}  {score_disp:.6f}  {raw_str:>6}  {e.get('final_tier') or 'unknown':<30}  {truncate_title(e['title'], opts.title_width)}{suffix}{neighbor_meta}"
                )
            else:
                out.append(
                    f"{i:>4}  {score_disp:.6f}  {truncate_title(e['title'], opts.title_width)}{suffix}"
                )
        out.append("")
        return out

    lines.extend(_fmt_table(f"# Top {len(top_n)} (score + title)", top_n, include_raw=False))
    lines.extend(_fmt_table(f"# Bottom {len(bottom_n)} (score + title)", bottom_n, include_raw=False))
    lines.extend(
        _fmt_table(
            f"# Top {len(top_n)} by HCI_v1_final_score (full detail)",
            top_n,
            include_raw=True,
            full_neighbor_meta=True,
        )
    )
    lines.extend(
        _fmt_table(
            f"# Bottom {len(bottom_n)} by HCI_v1_final_score (full detail)",
            bottom_n,
            include_raw=True,
            full_neighbor_meta=True,
        )
    )

    lines.append("# Full list (all entries, sorted by HCI_v1_final_score desc)")
    lines.append(f"{'rank':>4}  {'score':>6}  {'raw':>6}  {'tier':<30}  title")
    lines.append("-" * 72)
    for i, e in enumerate(entries, 1):
        raw = e.get("raw")
        raw_str = f"{raw:.3f}" if isinstance(raw, (int, float)) else "n/a"
        suffix = ""
        sidecar = e.get("sidecar_status") or "unknown"
        backend = e.get("tempo_backend_detail") or "unknown"
        if sidecar != "used" or backend not in ("essentia", "madmom"):
            suffix = f" [sidecar={sidecar}/{backend}]"
        meta_block = e.get("historical_echo_meta") or {}
        neighbor_meta = ""
        if meta_block:
            neighbor_meta = (
                f" [neighbors={meta_block.get('neighbors_total','?')}/{meta_block.get('neighbors_kept_inline','?')} "
                f"tiers={meta_block.get('neighbor_tiers','?')}]"
            )
        lines.append(
            f"{i:>4}  {effective_score(e):.6f}  {raw_str:>6}  {e.get('final_tier') or 'unknown':<30}  {truncate_title(e['title'], opts.title_width)}{suffix}{neighbor_meta}"
        )
    lines.append("")
    lines.append("# Notes:")
    lines.append("# - HCI_v1 is an audio-based historical-echo score, not a hit predictor.")
    lines.append("# - Tiers are shorthand labels: WIP-A+/A/B/C from the .hci.json files.")
    lines.append("# - Raw is the uncalibrated score (if present) for transparency.")
    lines.append("# - This report only includes files under the specified root.")
    lines.append("# - How to read: higher score = closer to long-run US Pop archetypes; tiers are qualitative labels around that score.")

    return 0, lines + [""], entries, top_n, bottom_n
