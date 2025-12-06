#!/usr/bin/env python3
"""
Build a simple run summary from emitted artifacts.
Uses schema helpers for lightweight parsing and emits a JSON summary with versions and artifact stats.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
import importlib

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()
from ma_audio_engine.adapters import di, load_log_settings
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from ma_audio_engine.schemas import Features, HCI, HistoricalEcho, dump_json
from tools.schema_utils import lint_json_file
from tools import names

from ma_audio_engine.schemas import CLIENTRich, lint_client_rich_text  # type: ignore


def gather_versions() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for mod in ("numpy", "scipy", "librosa"):
        try:
            out[mod] = importlib.import_module(mod).__version__
        except Exception:
            out[mod] = "missing"
    return out


def load_warnings(warn_path: Path) -> List[str]:
    if not warn_path.exists():
        return []
    try:
        data = json.loads(warn_path.read_text())
        if isinstance(data, list):
            return [str(w) for w in data]
    except Exception:
        return []
    return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Summarize pipeline run.")
    ap.add_argument("--out-dir", required=True, help="Output directory for artifacts (e.g., track folder or smoke output).")
    ap.add_argument("--warnings-json", default=None, help="Optional path to warnings JSON to include.")
    ap.add_argument("--strict", action="store_true", help="Exit non-zero if lint warnings are found.")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir).expanduser().resolve()
    settings = load_log_settings(args)
    log = di.make_logger("log_summary", structured=settings.log_json, defaults={"tool": "log_summary"}, redact=settings.log_redact, secrets=settings.log_redact_values)
    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        log("start", {"event": "start", "tool": "log_summary", "out_dir": str(out_dir), "warnings": bool(args.warnings_json)})
        log_stage_start(log, "log_summary", out_dir=str(out_dir), warnings=bool(args.warnings_json))

    summary: Dict[str, Any] = {
        "out_dir": str(out_dir),
        "pipeline_version": os.environ.get("PIPELINE_VERSION", "unknown"),
        "versions": gather_versions(),
        "warnings": [],
        "artifacts": {},
    }

    if args.warnings_json:
        summary["warnings"] = load_warnings(Path(args.warnings_json))

    # Populate artifact stats and basic schema info if present
    def _stat(name: str, filename_glob: str, loader=None):
        matches = list(out_dir.glob(filename_glob))
        if not matches:
            return
        p = matches[0]
        info: Dict[str, Any] = {"path": str(p), "bytes": p.stat().st_size}
        if loader:
            try:
                obj = loader(p)
                info.update(json.loads(json.dumps(obj, default=lambda o: o.__dict__)))
            except Exception:
                pass
        summary["artifacts"][name] = info

    feat_files = list(out_dir.glob("*.features.json"))
    if feat_files:
        _stat("features", "*.features.json", loader=lambda p: Features.from_json(p))
        try:
            feat_data = json.loads(feat_files[0].read_text())
            summary["pipeline_version"] = feat_data.get("pipeline_version") or summary.get("pipeline_version") or "unknown"
            summary["source_hash"] = feat_data.get("source_hash")
            summary["sidecar_status"] = feat_data.get("sidecar_status")
            summary["sidecar_attempts"] = feat_data.get("sidecar_attempts")
            if "sidecar_timeout_seconds" in feat_data:
                summary["sidecar_timeout_seconds"] = feat_data.get("sidecar_timeout_seconds")
        except Exception:
            pass
    _stat("sidecar", "*.sidecar.json", loader=None)
    merged_files = list(out_dir.glob("*.merged.json"))
    if merged_files:
        merged_path = merged_files[0]
        warns, _ = lint_json_file(merged_path, "merged")
        if warns:
            summary.setdefault("warnings", []).extend([f"merged:{w}" for w in warns])
        _stat("merged", "*.merged.json", loader=None)
    _stat("hci", "*.hci.json", loader=lambda p: HCI.from_json(p))
    for pattern in names.client_json_globs():
        _stat("client_json", pattern, loader=None)
    lint_failures = 0
    client_rich_files: List[Path] = []
    for pattern in names.client_rich_globs():
        client_rich_files.extend(out_dir.glob(pattern))
    if client_rich_files:
        client_file = client_rich_files[0]
        try:
            lint_warns = CLIENTRich.from_text(client_file) and []
        except Exception:
            lint_warns = ["invalid:client_rich_parse_error"]
        lint_warns.extend(lint_client_rich_text(client_file.read_text()))
        if lint_warns:
            summary.setdefault("warnings", []).extend([f"client_rich:{w}" for w in lint_warns])
            lint_failures += len(lint_warns)
        for pattern in names.client_rich_globs():
            _stat("client_rich", pattern, loader=lambda p: CLIENTRich.from_text(p))
    neighbor_files = list(out_dir.glob("*.neighbors.json"))
    if neighbor_files:
        npath = neighbor_files[0]
        warns, _ = lint_json_file(npath, "neighbors")
        if warns:
            summary.setdefault("warnings", []).extend([f"neighbors:{w}" for w in warns])
        _stat("neighbors", "*.neighbors.json", loader=lambda p: {"count": len(json.loads(p.read_text()).get("neighbors", []))})

    dest = out_dir / "run_summary.json"
    dump_json(dest, summary)
    # Self-lint run summary
    summary_warnings, _ = lint_json_file(dest, "run_summary")
    if summary_warnings:
        summary.setdefault("warnings", []).extend([f"run_summary:{w}" for w in summary_warnings])
        dump_json(dest, summary)
    print(f"[run_summary] wrote {dest}")
    status = "ok"
    if args.strict and summary.get("warnings"):
        status = "lint_failed"
    if os.getenv("LOG_JSON") == "1":
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        log_stage_end(
            log,
            "log_summary",
            status=status,
            out_dir=str(out_dir),
            duration_ms=duration_ms,
            artifacts_found=list(summary.get("artifacts", {}).keys()),
            warnings_count=len(summary.get("warnings", [])),
        )
        log("end", {"event": "end", "tool": "log_summary", "out_dir": str(out_dir), "status": status, "duration_ms": duration_ms, "warnings_count": len(summary.get("warnings", []))})
    if args.strict and summary.get("warnings"):
        raise SystemExit(f"strict mode: lint warnings present ({len(summary['warnings'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
