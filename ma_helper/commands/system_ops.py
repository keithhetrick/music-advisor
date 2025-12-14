"""System-level operations: github-check, sparse, preflight."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from typing import Callable

from ma_helper.core.env import ROOT
from ma_helper.commands.system import handle_preflight, handle_doctor


def run_github_check(args, *, require_confirm: Callable[[str], bool], cmd_verify: Callable[[argparse.Namespace], int], orch=None) -> int:
    ok = True

    def fail(msg: str):
        nonlocal ok
        ok = False
        print(f"[fail] {msg}")

    if shutil.which("git") is None:
        fail("git not found on PATH; cannot perform github-check.")
        return 1
    if not (ROOT / ".git").exists():
        fail("No .git directory at repo root; github-check expects a git repo.")
        return 1
    if args.require_clean or os.environ.get("MA_REQUIRE_CLEAN") == "1" or args.require_clean_env:
        try:
            res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
            if res.stdout.strip():
                fail("Git working tree is dirty; commit/stash before pushing.")
        except Exception:
            fail("Unable to check git status (ensure repo initialized).")
    if args.require_branch:
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
            branch = res.stdout.strip()
            if branch != args.require_branch:
                fail(f"On branch '{branch}' but expected '{args.require_branch}'.")
        except Exception:
            fail("Unable to read current branch (maybe detached HEAD?).")
    if args.require_upstream:
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=ROOT, capture_output=True, text=True, check=True)
            upstream = res.stdout.strip()
            print(f"[ma] upstream: {upstream}")
        except Exception:
            fail("No upstream tracking branch set; git rev-parse @{u} failed.")
    try:
        base_ref = args.base if getattr(args, "base", None) else "origin/main"
        res = subprocess.run(["git", "rev-list", "--left-right", "--count", f"{base_ref}...HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        ahead, behind = res.stdout.strip().split()
        print(f"[ma] ahead/behind vs {base_ref}: +{ahead} / -{behind}")
    except Exception:
        print("[ma] warning: unable to compute ahead/behind.", file=sys.stderr)
    if args.require_optional or os.environ.get("MA_REQUIRE_OPTIONAL") == "1":
        rc = handle_doctor(require_optional=True)
        if rc != 0:
            fail("Optional dependencies check failed (rich/watchfiles/entr/graphviz).")
    if args.preflight:
        if orch is None:
            fail("Preflight requested but no orchestrator adapter provided.")
        elif handle_preflight(orch) != 0:
            fail("Preflight failed (missing test/run paths).")
    if args.verify and cmd_verify(argparse.Namespace(ignore_failures=False)) != 0:
        fail("Verify failed.")
    if args.ci_plan:
        base = args.base or "origin/main"
        print(f"[ma] ci-plan dry-run vs {base}:")
        subprocess.call(["python", "-m", "ma_helper", "ci-plan", "--base", base, "--targets", "test", "--matrix"], cwd=ROOT)
    return 0 if ok else 1


def handle_sparse_cli(args, require_confirm, run_cmd) -> int:
    if args.list:
        return run_cmd("git sparse-checkout list", cwd=ROOT)
    if args.reset:
        if not require_confirm("Disable sparse-checkout?"):
            print("[ma] aborting (strict guard).")
            return 1
        return run_cmd("git sparse-checkout disable", cwd=ROOT)
    if args.set:
        paths = args.set
        print(f"[ma] enabling cone mode and setting paths: {paths}")
        rc = run_cmd("git sparse-checkout init --cone", cwd=ROOT)
        if rc != 0:
            return rc
        return run_cmd("git sparse-checkout set " + " ".join(paths), cwd=ROOT)
    print("Usage: sparse --list | --reset | --set <paths...>")
    return 1
