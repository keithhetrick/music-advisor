"""System/doctor/guard/preflight helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Dict

from ma_helper.core.env import ROOT
from ma_helper.commands.ux import render_error_panel
from ma_helper.core.state import guard_level, set_guard_level


def handle_guard(args) -> int:
    level = guard_level()
    if args.set:
        set_guard_level(args.set)
        print(f"[ma] guard set to {args.set}")
        return 0
    print(f"[ma] guard: {level}")
    return 0


def handle_check() -> int:
    # simple check for git status, venv, watch deps
    issues = []
    if os.environ.get("VIRTUAL_ENV") is None:
        issues.append("venv not active")
    if shutil.which("git") is None:
        issues.append("git missing")
    if shutil.which("entr") is None and shutil.which("watchfiles") is None:
        issues.append("entr/watchfiles missing (for watch)")
    if issues:
        print("[ma] check issues:")
        for i in issues:
            print(f"- {i}")
        return 1
    print("[ma] check passed.")
    return 0


def handle_preflight(orch) -> int:
    reg = orch.load_projects()
    missing = []
    for name, proj in reg.items():
        p = ROOT / proj.path
        if not p.exists():
            missing.append((name, proj.path))
        for t in proj.tests:
            if not (ROOT / t).exists():
                missing.append((name, t))
    if not missing:
        print("[ma] preflight OK")
        return 0
    print("[ma] missing paths:")
    for name, path in missing:
        print(f"- {name}: {path}")
    return 1


def _test_gaps(projects) -> tuple[list[str], list[str]]:
    missing_decl = []
    missing_paths = []
    if not projects:
        return missing_decl, missing_paths
    for proj in projects.values():
        tests = getattr(proj, "tests", None)
        if not tests:
            missing_decl.append(proj.name)
            continue
        for t in tests:
            if not (ROOT / t).exists():
                missing_paths.append(f"{proj.name}: {t}")
    return missing_decl, missing_paths


def handle_doctor(require_optional: bool, interactive: bool = False, check_tests: bool = False, projects=None) -> int:
    missing = []
    required = ["python3", "git"]
    optional = ["rich", "textual", "watchfiles", "entr", "dot"]
    for tool in required:
        if shutil.which(tool) is None:
            missing.append(tool)
    opt_missing = [tool for tool in optional if shutil.which(tool) is None]
    if missing or (require_optional and opt_missing):
        lines = []
        if missing:
            lines.append("Missing required: " + ", ".join(missing))
        if require_optional and opt_missing:
            lines.append("Missing optional: " + ", ".join(opt_missing))
        suggestions = []
        if interactive:
            if missing:
                suggestions.append("Install required tools (brew/apt/yum): " + " ".join(missing))
            if require_optional and opt_missing:
                suggestions.append("Install optional tools: " + " ".join(opt_missing))
        render_error_panel("Doctor detected issues.\n" + "\n".join(lines), suggestions if suggestions else None)
        return 1
    test_decl_missing: list[str] = []
    test_path_missing: list[str] = []
    if check_tests and projects:
        test_decl_missing, test_path_missing = _test_gaps(projects)
        if test_decl_missing or test_path_missing:
            msgs = []
            if test_decl_missing:
                msgs.append("No tests declared: " + ", ".join(sorted(test_decl_missing)))
            if test_path_missing:
                msgs.append("Missing test paths:\n" + "\n".join(f" - {p}" for p in sorted(test_path_missing)))
            suggestions = []
            if interactive:
                suggestions.append("Add test paths to project_map.json for missing projects.")
                suggestions.append("Create the missing test files or update the registry paths.")
            if interactive:
                suggestions.append("Re-run: ma doctor --check-tests")
            render_error_panel("Doctor: test coverage gaps detected.\n" + "\n".join(msgs), suggestions if suggestions else None)
            return 1
    if opt_missing:
        print("[ma] optional tools not found: " + ", ".join(opt_missing))
        if interactive:
            print("[ma] install optional tools for best UX: rich watchfiles entr graphviz")
    print("[ma] doctor OK")
    if interactive:
        print("[ma] remediation tips:")
        print("- Verify git upstream: ma github-check --require-upstream")
        print("- Confirm tests declared: ma doctor --check-tests")
        print("- Run quickstart: ma quickstart")
    return 0
