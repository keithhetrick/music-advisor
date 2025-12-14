"""Git-related command handlers."""
from __future__ import annotations

import subprocess
import sys
from typing import Optional

from ma_helper.core.env import ROOT
from ma_helper.core.git import git_summary


def _git_basic_status():
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        branch = "unknown"
    try:
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        dirty = "dirty" if dirty else "clean"
    except Exception:
        dirty = "unknown"
    return branch, dirty


def handle_git_branch(args) -> int:
    project = args.project.replace("/", "-")
    desc = args.desc.replace(" ", "-")
    branch_name = f"{args.prefix}/{project}-{desc}"
    print(f"[ma] creating branch {branch_name}")
    rc = subprocess.call(["git", "checkout", "-b", branch_name], cwd=ROOT)
    if rc != 0:
        return rc
    if args.upstream:
        rc = subprocess.call(["git", "push", "-u", args.upstream, branch_name], cwd=ROOT)
        if rc != 0:
            return rc
    if args.sparse:
        paths = args.sparse
        subprocess.call(["git", "sparse-checkout", "set", "--cone", *paths], cwd=ROOT)
    return 0


def handle_git_status(args) -> int:
    summary = git_summary()
    if getattr(args, "json", False):
        import json

        print(json.dumps(summary, indent=2))
        return 0
    branch = summary.get("branch")
    dirty = summary.get("dirty")
    ahead = summary.get("ahead")
    behind = summary.get("behind")
    print(f"branch: {branch}, tree: {dirty}, ahead/behind: {ahead}/{behind}")
    if getattr(args, "branches", False):
        limit = getattr(args, "limit", 10) or 10
        try:
            res = subprocess.check_output(
                [
                    "git",
                    "for-each-ref",
                    "--count",
                    str(limit),
                    "--sort=-committerdate",
                    "--format",
                    "%(refname:short)|%(objectname:short)|%(authorname)|%(committerdate:relative)|%(contents:subject)",
                    "refs/heads",
                ],
                cwd=ROOT,
                text=True,
            )
            lines = [ln for ln in res.strip().splitlines() if ln.strip()]
            if lines:
                print("Local branches (recent):")
                for ln in lines:
                    parts = ln.split("|")
                    if len(parts) >= 5:
                        name, sha, author, age, subj = parts[:5]
                        marker = "*" if name == branch else " "
                        print(f"{marker} {name:<28} {sha:<10} {age:<12} {author:<14} {subj}")
        except Exception:
            print("[ma] warning: unable to list branches (git for-each-ref failed)", file=sys.stderr)
    return 0


def handle_git_upstream(args) -> int:
    branch = args.branch
    if not branch:
        try:
            branch = (
                subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True)
                .strip()
            )
        except Exception:
            print("[ma] failed to detect current branch", file=sys.stderr)
            return 1
    rc = subprocess.call(["git", "push", "-u", args.remote, branch], cwd=ROOT)
    return rc


def handle_git_rebase(args) -> int:
    target = args.onto
    print(f"[ma] rebasing onto {target}")
    return subprocess.call(["git", "rebase", target], cwd=ROOT)


def handle_git_pull_check(args) -> int:
    remote = args.remote
    branch = args.branch
    if not branch:
        try:
            branch = (
                subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True)
                .strip()
            )
        except Exception:
            print("[ma] failed to detect current branch", file=sys.stderr)
            return 1
    # optional clean check
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
    if status.stdout.strip():
        print("[ma] working tree dirty; aborting pull-check", file=sys.stderr)
        return 1
    return subprocess.call(["git", "pull", remote, branch], cwd=ROOT)
