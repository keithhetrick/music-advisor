"""Git change detection and affected graph helpers."""
from __future__ import annotations

import subprocess
import sys
from typing import Dict, List, Tuple

from .state import load_favorites, set_last_base


def resolve_base(base_arg: str, base_from: str | None) -> str:
    if base_from == "last":
        stored = load_favorites().get("last_base")
        if stored:
            print(f"[ma] using last base from config: {stored}")
            set_last_base(stored)
            return stored
        print("[ma] no last base recorded; falling back to provided --base.")
    set_last_base(base_arg)
    return base_arg


def collect_changes(orch, base: str, merge_base: bool = False, since: str | None = None) -> List[str]:
    ref = base or "origin/main"
    if since:
        try:
            proc = subprocess.run(
                ["git", "log", f"--since={since}", "--name-only", "--pretty=format:"],
                cwd=orch.ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
            return list(dict.fromkeys(lines))  # preserve order/unique
        except subprocess.CalledProcessError as exc:
            print(f"[ma] git log --since failed ({exc}); falling back to all.", file=sys.stderr)
            return []
    diff_ref = ref
    if merge_base:
        try:
            mb = (
                subprocess.run(["git", "merge-base", ref, "HEAD"], cwd=orch.ROOT, text=True, capture_output=True, check=True)
                .stdout.strip()
            )
            if mb:
                diff_ref = mb
                print(f"[ma] using merge-base {mb} for base {ref}")
        except subprocess.CalledProcessError as exc:
            print(f"[ma] merge-base failed ({exc}); using base {ref}", file=sys.stderr)
    diff_args = [f"{diff_ref}...HEAD"]
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", *diff_args],
            cwd=orch.ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as exc:
        print(f"[ma] git diff failed ({exc}); falling back to full test-all.", file=sys.stderr)
        return []


def _collect_and_match_changes(orch, projects, base: str, since: str | None, merge_base: bool):
    changes = collect_changes(orch, base, merge_base=merge_base, since=since)
    if not changes:
        names = [n for n, p in projects.items() if p.tests]
        mode = "all" if not since else "since-empty"
        return names, [], mode
    direct = orch.match_projects_for_paths(projects, changes)
    dependents = orch.build_dependents_map(projects)
    affected = orch.expand_with_dependents(direct, dependents)
    names = [n for n in projects if n in affected and projects[n].tests]
    mode = "since" if since else "affected"
    return names, changes, mode


def compute_affected(orch, projects, base: str, no_diff: bool, *, since: str | None = None, merge_base: bool = False):
    if no_diff:
        names = [n for n, p in projects.items() if p.tests]
        return names, [], "no-diff"
    return _collect_and_match_changes(orch, projects, base, since=since, merge_base=merge_base)
