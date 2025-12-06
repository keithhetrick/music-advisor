#!/usr/bin/env python3
"""
hci_rank_from_folder.py

Scan a folder (e.g., features_output/2025/11/25) for *.hci.json files and
produce a ranking of tracks by HCI_v1_final_score (desc/asc).

Usage:
  python tools/hci_rank_from_folder.py --root features_output/2025/11/25
  python tools/hci_rank_from_folder.py --root features_output/2025/11/25 --out /tmp/hci_rank.txt --top 20
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import (
    add_log_sandbox_arg,
    add_qa_policy_arg,
    apply_log_sandbox_env,
    di,
    load_log_settings,
    load_qa_policy,
    make_logger,
    require_file,
    resolve_config_value,
    validate_root_dir,
)
from tools.hci.hci_rank_service import RankOptions, effective_score, filter_entries, load_hci_score, render_report

LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
_log = make_logger("hci_rank", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)


def _log_info(msg: str) -> None:
    _log(msg)


def _log_warn(msg: str) -> None:
    _log(msg)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rank HCI_v1 scores within a folder of *.hci.json files.")
    p.add_argument("--root", required=True, help="Folder(s) containing *.hci.json files (comma-separated allowed).")
    p.add_argument("--out", default=None, help="Output text file (default: <root>/hci_rank_summary.txt).")
    p.add_argument("--top", type=int, default=10, help="Number of top/bottom entries to show (default: 10).")
    p.add_argument("--csv-out", default=None, help="Optional CSV output with all rows (title,score,raw,tier,path).")
    p.add_argument("--markdown-out", default=None, help="Optional Markdown output file.")
    p.add_argument(
        "--tiers",
        default=None,
        help="Optional comma list of tiers to include (e.g., 'WIP-A+,WIP-A'); defaults to all.",
    )
    p.add_argument("--min-score", type=float, default=None, help="Only include scores >= this value.")
    p.add_argument("--max-score", type=float, default=None, help="Only include scores <= this value.")
    p.add_argument("--title-width", type=int, default=None, help="Optional title width to truncate for tables.")
    p.add_argument(
        "--qa-strict",
        action="store_true",
        help="Exclude entries whose feature QA gate is not pass/ok.",
    )
    add_qa_policy_arg(
        p, env_var="QA_POLICY"
    )
    p.add_argument(
        "--qa-penalty",
        type=float,
        default=0.0,
        help="If >0, apply a multiplicative penalty to scores with QA warnings (default: 0 = off).",
    )
    p.add_argument(
        "--summarize-qa",
        action="store_true",
        help="Print QA/cache/config summary counts in the report (non-destructive).",
    )
    p.add_argument(
        "--fail-on-config-drift",
        action="store_true",
        help="If multiple config_fingerprints or pipeline_versions are present, abort the run.",
    )
    p.add_argument(
        "--unknown-qa",
        choices=["pass", "warn", "drop"],
        default="warn",
        help="How to treat entries with missing/unknown QA gate (default: warn = include but mark).",
    )
    p.add_argument(
        "--require-sidecar-backend",
        choices=["any", "essentia_madmom"],
        default="any",
        help="Drop entries if sidecar backend is not Essentia/Madmom (or not used) when set to 'essentia_madmom'.",
    )
    p.add_argument(
        "--show-sidecar-meta",
        action="store_true",
        help="Include sidecar backend/confidence in top/bottom summaries (diagnostic).",
    )
    p.add_argument(
        "--require-neighbors-file",
        action="store_true",
        help="Drop entries that do not have a neighbors_file in historical_echo_meta or neighbors_total == 0.",
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
    return p.parse_args()


def rank_folder(roots: List[Path], args: argparse.Namespace, qa_policy_name: str) -> int:
    tiers_filter = None
    if args.tiers:
        tiers_filter = {t.strip() for t in args.tiers.split(",") if t.strip()}

    out_path = Path(args.out) if args.out else (roots[0] / "hci_rank_summary.txt")

    entries: List[Dict[str, Any]] = []
    for root in roots:
        for hci_path in root.rglob("*.hci.json"):
            res = load_hci_score(hci_path)
            if res:
                if tiers_filter and (res.get("final_tier") not in tiers_filter):
                    continue
                if args.min_score is not None and res["score"] < args.min_score:
                    continue
                if args.max_score is not None and res["score"] > args.max_score:
                    continue
                entries.append(res)

    filtered_entries: List[Dict[str, Any]] = []
    supported_backends = list_supported_backends()
    qa_counts = {}
    cache_counts = {}
    config_set = set()
    pipeline_versions = set()
    freshness_counts = {}
    audio_fresh_counts = {}
    sidecar_counts = {}
    sidecar_backend_counts = {}
    sidecar_warn_counts = {}
    for e in entries:
        gate_raw = e.get("qa_gate")
        gate = (gate_raw or "").lower()
        if gate in ("", "unknown", None):
            if args.unknown_qa == "drop":
                continue
            if args.unknown_qa == "warn":
                gate = "unknown"
            else:
                gate = "pass"
        if qa_policy_name == "strict" and gate not in ("pass", "ok"):
            continue
        score_eff = e["score"]
        penalty_applied = False
        if args.qa_penalty > 0 and gate not in ("", "pass", "ok"):
            score_eff = e["score"] / (1.0 + args.qa_penalty)
            penalty_applied = True
        if args.require_sidecar_backend == "essentia_madmom":
            if e.get("sidecar_status") != "used" or e.get("tempo_backend_detail") not in ("essentia", "madmom"):
                continue
        if args.require_neighbors_file:
            meta = e.get("historical_echo_meta") or {}
            if not meta.get("neighbors_file") or not meta.get("neighbors_total"):
                continue
        e["score_effective"] = score_eff
        e["qa_penalty_applied"] = penalty_applied
        filtered_entries.append(e)

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
                _log_warn(
                    f"[hci_rank] WARN: tempo backend '{backend}' not in registry {supported_backends}; "
                    "consider updating config/backend_registry.json."
                )
            elif not is_backend_enabled(backend):
                _log_warn(
                    f"[hci_rank] WARN: tempo backend '{backend}' is disabled in registry; "
                    "rank output may mix preferred and non-preferred backends."
                )
        warns = e.get("sidecar_warnings")
        if isinstance(warns, list):
            for w in warns:
                sidecar_warn_counts[w or "unspecified"] = sidecar_warn_counts.get(w or "unspecified", 0) + 1
        elif warns:
            sidecar_warn_counts[str(warns)] = sidecar_warn_counts.get(str(warns), 0) + 1

    entries = filtered_entries

    if not entries:
        out_path.write_text("No valid *.hci.json scores found.\n")
        _log_info(f"[hci_rank] No scores found under {', '.join(str(r) for r in roots)}")
        return 0

    entries.sort(key=lambda x: effective_score(x), reverse=True)
    top_n = entries[: args.top]
    bottom_n = entries[-args.top :] if len(entries) > args.top else entries

    scores_eff = [effective_score(e) for e in entries]
    max_score = max(scores_eff) if scores_eff else None
    min_score = min(scores_eff) if scores_eff else None
    median = None
    if scores_eff:
        sorted_scores_eff = sorted(scores_eff)
        n = len(sorted_scores_eff)
        mid = n // 2
        if n % 2 == 0:
            median = (sorted_scores_eff[mid - 1] + sorted_scores_eff[mid]) / 2
        else:
            median = sorted_scores_eff[mid]

    lines: List[str] = []
    lines.append("# ==== HCI_v1 Ranking Report ====")
    lines.append(f"# Roots: {', '.join(str(r) for r in roots)}")
    lines.append(f"# Generated: {utc_now_iso(timespec='seconds')}")
    lines.append(f"# Total tracks: {len(entries)}")
    lines.append("# Legend: score = HCI_v1_final_score (audio-based historical echo); higher = closer to long-run US Pop archetypes; tier is the qualitative label.")
    lines.append(f"# Filtered tiers: {','.join(sorted(tiers_filter)) if tiers_filter else 'all'}")
    lines.append(f"# QA: policy={qa_policy_name} | penalty_factor={args.qa_penalty}")
    if scores_eff:
        lines.append(f"# Stats: max={max_score:.3f} | min={min_score:.3f} | median={median:.3f}")
    if entries:
        tier_counts: Dict[str, int] = {}
        for e in entries:
            tier = e.get("final_tier") or "unknown"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        counts_str = ", ".join(f"{k}: {v}" for k, v in sorted(tier_counts.items()))
        lines.append(f"# Tier counts: {counts_str}")
    if args.summarize_qa:
        lines.append(f"# QA gates: {dict(sorted(qa_counts.items()))}")
        lines.append(f"# Cache status: {dict(sorted(cache_counts.items()))}")
        lines.append(f"# Sidecar status: {dict(sorted(sidecar_counts.items()))}")
        lines.append(f"# Sidecar backends: {dict(sorted(sidecar_backend_counts.items()))}")
        if sidecar_warn_counts:
            lines.append(f"# Sidecar warnings: {dict(sorted(sidecar_warn_counts.items()))}")
        if config_set:
            lines.append(f"# Config fingerprints ({len(config_set)}): {sorted(config_set)}")
        if pipeline_versions:
            lines.append(f"# Pipeline versions ({len(pipeline_versions)}): {sorted(pipeline_versions)}")
        lines.append(f"# Feature freshness: {dict(sorted(freshness_counts.items()))}")
        lines.append(f"# Audio vs feature freshness: {dict(sorted(audio_fresh_counts.items()))}")
        if len(config_set) > 1:
            lines.append("# WARNING: multiple config_fingerprint values detected; mixed extractor settings in this batch.")
        if args.fail_on_config_drift and (len(config_set) > 1 or len(pipeline_versions) > 1):
            lines.append("# ERROR: config drift detected and --fail-on-config-drift is set; aborting.")
            out_path.write_text("\n".join(lines) + "\n")
            _log_warn(f"[hci_rank] Config drift detected; wrote summary to {out_path} and exiting due to --fail-on-config-drift.")
            return 1
    lines.append("")
def main() -> None:
    args = parse_args()
    global _log
    apply_log_sandbox_env(args)
    redact_flag = args.log_redact or LOG_REDACT
    redact_values = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or LOG_REDACT_VALUES
    )
    log_settings = load_log_settings(args)
    redact_flag = redact_flag or log_settings.log_redact
    redact_values = redact_values or log_settings.log_redact_values
    _log = di.make_logger(
        "hci_rank",
        structured=os.getenv("LOG_JSON") == "1",
        defaults={"tool": "hci_rank"},
        redact=redact_flag,
        secrets=redact_values,
    )
    qa_policy_name = resolve_config_value(args.qa_policy, env_var="QA_POLICY", default="default")
    # Load QA policy through adapter so future overrides/configs are picked up without code changes.
    qa_policy = load_qa_policy(qa_policy_name)
    _ = qa_policy  # currently only used for modular hook; retained for future thresholds
    if args.qa_strict and qa_policy_name != "strict":
        qa_policy_name = "strict"
    validate_root_dir(args.root, logger=_log_warn)

    roots: List[Path] = []
    for r in args.root.split(","):
        r = r.strip()
        if not r:
            continue
        p = Path(r)
        require_file(p, desc="root folder", is_dir=True)
        roots.append(p)
    if not roots:
        raise FileNotFoundError("No valid root provided.")

    out_path = Path(args.out) if args.out else (roots[0] / "hci_rank_summary.txt")

    tiers_filter = [t.strip() for t in args.tiers.split(",")] if args.tiers else None

    entries: List[Dict[str, Any]] = []
    for root in roots:
        for hci_path in root.rglob("*.hci.json"):
            res = load_hci_score(hci_path, logger=_log_warn)
            if res:
                entries.append(res)

    opts = RankOptions(
        qa_policy_name="strict" if args.qa_strict or qa_policy_name == "strict" else qa_policy_name,
        qa_penalty=args.qa_penalty,
        unknown_qa=args.unknown_qa,
        require_sidecar_backend=args.require_sidecar_backend,
        require_neighbors_file=args.require_neighbors_file,
        tiers_filter=tiers_filter,
        min_score=args.min_score,
        max_score=args.max_score,
        top=args.top,
        title_width=args.title_width,
        show_sidecar_meta=args.show_sidecar_meta,
        summarize_qa=args.summarize_qa,
        fail_on_config_drift=args.fail_on_config_drift,
    )

    entries, meta = filter_entries(entries, opts, log_warn=_log_warn)
    status, lines, entries, top_n, bottom_n = render_report(roots, entries, opts, meta)
    if not entries:
        out_path.write_text("\n".join(lines))
        _log_info(f"[hci_rank] No scores found under {', '.join(str(r) for r in roots)}")
        return status

    # Render report
    out_path.write_text("\n".join(lines))
    _log_info(f"[hci_rank] Wrote ranking to {out_path}")

    # Optional CSV output
    if args.csv_out:
        csv_path = Path(args.csv_out)
        import csv

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["title", "score", "raw", "tier", "path"])
            for e in entries:
                raw = e.get("raw")
                writer.writerow(
                    [
                        e["title"],
                        f"{effective_score(e):.3f}",
                        f"{raw:.3f}" if isinstance(raw, (int, float)) else "",
                        e.get("final_tier") or "",
                        e["path"],
                    ]
                )
        _log_info(f"[hci_rank] Wrote CSV to {csv_path}")

    # Optional Markdown output
    if args.markdown_out:
        md_path = Path(args.markdown_out)
        scores_eff = [effective_score(e) for e in entries]
        max_score = max(scores_eff) if scores_eff else None
        min_score = min(scores_eff) if scores_eff else None
        median = None
        if scores_eff:
            sorted_scores_eff = sorted(scores_eff)
            n = len(sorted_scores_eff)
            mid = n // 2
            median = (sorted_scores_eff[mid - 1] + sorted_scores_eff[mid]) / 2 if n % 2 == 0 else sorted_scores_eff[mid]
        tier_counts: Dict[str, int] = {}
        for e in entries:
            tier = e.get("final_tier") or "unknown"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        counts_str = ", ".join(f"{k}: {v}" for k, v in sorted(tier_counts.items())) if tier_counts else ""
        md_lines: List[str] = []
        md_lines.append(f"# HCI_v1 Ranking Report")
        md_lines.append("")
        md_lines.append(f"- **Roots:** {', '.join(str(r) for r in roots)}")
        md_lines.append(f"- **Total tracks:** {len(entries)}")
        md_lines.append(f"- **Filtered tiers:** {','.join(sorted(tiers_filter)) if tiers_filter else 'all'}")
        md_lines.append(f"- **Generated:** {utc_now_iso(timespec='seconds')}")
        if scores_eff:
            md_lines.append(f"- **Stats:** max={max_score:.3f} | min={min_score:.3f} | median={median:.3f}")
        if entries:
            md_lines.append(f"- **Tier counts:** {counts_str if scores_eff else 'n/a'}")
        md_lines.append("")
        md_lines.append("## Top by HCI_v1_final_score")
        md_lines.append("| rank | score | raw | tier | title |")
        md_lines.append("| ---: | ---: | ---: | :--- | :--- |")
        for i, e in enumerate(top_n, 1):
            raw = e.get("raw")
            raw_str = f"{raw:.3f}" if isinstance(raw, (int, float)) else "n/a"
            md_lines.append(f"| {i} | {effective_score(e):.3f} | {raw_str} | {e.get('final_tier') or 'unknown'} | {truncate_title(e['title'], args.title_width)} |")
        md_lines.append("")
        md_lines.append("## Bottom by HCI_v1_final_score")
        md_lines.append("| rank | score | raw | tier | title |")
        md_lines.append("| ---: | ---: | ---: | :--- | :--- |")
        for i, e in enumerate(bottom_n, 1):
            raw = e.get("raw")
            raw_str = f"{raw:.3f}" if isinstance(raw, (int, float)) else "n/a"
            md_lines.append(f"| {i} | {effective_score(e):.3f} | {raw_str} | {e.get('final_tier') or 'unknown'} | {truncate_title(e['title'], args.title_width)} |")
        md_lines.append("")
        md_lines.append("## Full list (all entries)")
        md_lines.append("| rank | score | raw | tier | title |")
        md_lines.append("| ---: | ---: | ---: | :--- | :--- |")
        for i, e in enumerate(entries, 1):
            raw = e.get("raw")
            raw_str = f"{raw:.3f}" if isinstance(raw, (int, float)) else "n/a"
            md_lines.append(f"| {i} | {effective_score(e):.3f} | {raw_str} | {e.get('final_tier') or 'unknown'} | {e['title']} |")
        md_lines.append("")
        md_lines.append("## Notes")
        md_lines.append("- HCI_v1 is an audio-based historical-echo score, not a hit predictor.")
        md_lines.append("- Tiers are shorthand labels: WIP-A+/A/B/C from the .hci.json files.")
        md_lines.append("- Raw is the uncalibrated score (if present) for transparency.")
        md_lines.append("- This report only includes files under the specified root.")
        md_lines.append("- How to read: higher score = closer to long-run US Pop archetypes; tiers are qualitative labels around that score.")

        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        _log_info(f"[hci_rank] Wrote Markdown to {md_path}")

    return status

if __name__ == "__main__":
    raise SystemExit(main())
