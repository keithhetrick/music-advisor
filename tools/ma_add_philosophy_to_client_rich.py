#!/usr/bin/env python3
"""
ma_add_philosophy_to_client_rich.py

Inject a compact PHILOSOPHY line into all .client.rich.txt files under a root.

- Reads HCI_v1_philosophy from the matching .hci.json when available.
- Produces a single-line comment of the form:

    # PHILOSOPHY: <tagline> HCI_v1 is a measure of Historical Echo — not a hit predictor.

- Inserts this line immediately after the '# HCI_V1_SUMMARY' header if present;
  otherwise, prepends it at the top.

Example:
    python tools/ma_add_philosophy_to_client_rich.py \
      --root features_output/2025/11/18
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from ma_audio_engine.adapters import add_log_sandbox_arg, add_log_format_arg, add_preflight_arg, apply_log_sandbox_env, apply_log_format_env, run_preflight_if_requested
from ma_audio_engine.adapters import load_log_settings, load_runtime_settings
from ma_audio_engine.adapters import utc_now_iso
from shared.ma_utils.schema_utils import lint_json_file
from ma_audio_engine.adapters import di
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from ma_audio_engine.schemas import dump_json
from shared.ma_utils import get_configured_logger
from tools.philosophy_services import inject_philosophy_line_into_client, build_philosophy_line as build_philosophy_line_from_hci
from tools import names


DEFAULT_TAGLINE = "Top 40 ≈ Top 40(-40y), re-parameterized."


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def derive_hci_path_for_client(client_path: Path) -> Path:
    """
    Given a client rich path, derive the matching *.hci.json path.

    Example:
      'Foo.client.rich.txt' -> 'Foo.hci.json'
    """
    name = client_path.name
    if name.endswith(names.client_rich_suffix()):
        prefix = name[: -len(names.client_rich_suffix())]
        return client_path.with_name(prefix + ".hci.json")
    # Fallback: just swap extension
    stem = client_path.stem
    return client_path.with_name(stem + ".hci.json")


def build_philosophy_line(hci_path: Path, *, default_tagline: str = DEFAULT_TAGLINE) -> str:
    return build_philosophy_line_from_hci(default_tagline=default_tagline, hci_path=hci_path)


def inject_into_text(text: str, line: str) -> str:
    return inject_philosophy_line_into_client(text, line)


def process_client_file(client_path: Path, *, default_tagline: str = DEFAULT_TAGLINE) -> tuple[bool, list[str]]:
    try:
        text = client_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Failed to read {client_path}: {e}")
        return False, [f"{client_path.name}:read_error:{e}"]

    hci_path = derive_hci_path_for_client(client_path)
    line = build_philosophy_line(hci_path, default_tagline=default_tagline)

    new_text = inject_into_text(text, line)
    if new_text == text:
        return False, []

    try:
        client_path.write_text(new_text, encoding="utf-8")
        kind = "client_rich"
        lint_warns, _ = lint_json_file(client_path, kind)
        return True, [f"{client_path.name}:{w}" for w in lint_warns]
    except Exception as e:
        print(f"[WARN] Failed to write {client_path}: {e}")
        return False, [f"{client_path.name}:write_error:{e}"]

def main() -> None:
    ap = argparse.ArgumentParser(description=f"Inject PHILOSOPHY line into .{names.CLIENT_TOKEN}.rich.txt files.")
    ap.add_argument(
        "--root",
        required=True,
        help="Root directory to scan (e.g. features_output/2025/11/18)",
    )
    ap.add_argument(
        "--tagline",
        default=DEFAULT_TAGLINE,
        help="Override the default PHILOSOPHY tagline string.",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help=f"Exit non-zero if lint warnings are present in modified .{names.CLIENT_TOKEN}.rich.txt files.",
    )
    add_log_sandbox_arg(ap)
    add_log_format_arg(ap)
    add_preflight_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    apply_log_format_env(args)
    run_preflight_if_requested(args)
    # Load runtime settings to align env/config defaults across CLIs.
    _ = load_runtime_settings(args)
    _log = get_configured_logger("add_philosophy", defaults={"tool": "add_philosophy"})

    tagline = args.tagline or DEFAULT_TAGLINE

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")
    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        _log("start", {"event": "start", "tool": "add_philosophy", "root": str(root)})
        log_stage_start(_log, "add_philosophy_client", root=str(root))

    client_files = []
    for pattern in names.client_rich_globs():
        client_files.extend(sorted(root.rglob(pattern)))
    if not client_files:
        print(f"[INFO] No .{names.CLIENT_TOKEN}.rich.txt files found under {root}")
        return

    changed = 0
    warnings: list[str] = []
    for p in client_files:
        updated, warns = process_client_file(p, default_tagline=tagline)
        if updated:
            changed += 1
        warnings.extend(warns)

    timestamp = utc_now_iso()
    _log(f"[DONE] {timestamp} processed {len(client_files)} .{names.CLIENT_TOKEN}.rich.txt files; updated {changed} of them.")
    status = "ok"
    if warnings and args.strict:
        status = "error"

    if os.getenv("LOG_JSON") == "1":
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        log_stage_end(
            _log,
            "add_philosophy_client",
            status=status,
            root=str(root),
            processed=len(client_files),
            updated=changed,
            duration_ms=duration_ms,
            warnings=warnings,
        )
        _log("end", {"event": "end", "tool": "add_philosophy", "root": str(root), "status": status, "processed": len(client_files), "updated": changed, "duration_ms": duration_ms, "warnings": warnings})

    if warnings and args.strict:
        raise SystemExit("strict mode: lint warnings present")


if __name__ == "__main__":
    main()
