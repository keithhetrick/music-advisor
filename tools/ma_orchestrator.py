#!/usr/bin/env python3
"""
Lightweight project-aware orchestrator for the Music Advisor monorepo.

This mimics the useful parts of Nx/Turborepo without extra tooling:
  - Project registry loaded from project_map.json.
  - Per-project test execution via pytest and the repo env shim.
  - Affected detection via git diff with simple dependent expansion.
  - Unified entrypoint from the repo root (`python tools/ma_orchestrator.py ...`).

Future helpers (Nx/Pants) can map targets directly to the project names/paths
defined here, using the same commands for test/run entrypoints.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

ROOT = Path(__file__).resolve().parents[1]
PROJECT_MAP_PATH = ROOT / "project_map.json"
WITH_REPO_ENV = ROOT / "infra" / "scripts" / "with_repo_env.sh"


@dataclass(frozen=True)
class Project:
    name: str
    path: Path
    tests: List[str]
    description: str
    deps: List[str]
    type: str
    run: List[str] | None = None


def load_projects() -> Dict[str, Project]:
    raw = json.loads(PROJECT_MAP_PATH.read_text())
    projects: Dict[str, Project] = {}
    for name, meta in raw.items():
        tests = [str(t) for t in meta.get("tests", [])]
        deps = [str(d) for d in meta.get("deps", [])]
        run_val = meta.get("run")
        run_cmd = [str(part) for part in run_val] if isinstance(run_val, list) else None
        projects[name] = Project(
            name=name,
            path=ROOT / meta["path"],
            tests=tests,
            description=meta.get("description", ""),
            deps=deps,
            type=meta.get("type", "misc"),
            run=run_cmd,
        )
    return projects


def list_projects(projects: Dict[str, Project]) -> int:
    print("Projects (name: type -> path):")
    for name, project in projects.items():
        tests_label = ", ".join(project.tests) if project.tests else "none"
        deps_label = ", ".join(project.deps) if project.deps else "none"
        run_label = "yes" if project.run else "no"
        print(f"- {name}: {project.type} -> {project.path.relative_to(ROOT)}")
        if project.description:
            print(f"    {project.description}")
        print(f"    tests: {tests_label}")
        print(f"    deps: {deps_label}")
        print(f"    run target: {run_label}")
    return 0


def run_subprocess(cmd: Sequence[str], *, cwd: Path | None = None) -> int:
    pretty = " ".join(cmd)
    print(f"[ma] {pretty}")
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    return result.returncode


def run_tests_for_project(project: Project) -> int:
    if not project.tests:
        print(f"[ma] {project.name}: no tests configured, skipping.")
        return 0
    cmd = [str(WITH_REPO_ENV), "-m", "pytest", *project.tests]
    return run_subprocess(cmd)


def run_all_tests(projects: Dict[str, Project]) -> int:
    failures: List[str] = []
    for name, project in projects.items():
        if not project.tests:
            continue
        rc = run_tests_for_project(project)
        if rc != 0:
            failures.append(name)
    if failures:
        print(f"[ma] failed projects: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


def changed_files(base_ref: str) -> List[str]:
    ref = base_ref or "origin/main"
    diff_args = [ref] if "..." in ref else [f"{ref}...HEAD"]
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", *diff_args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[ma] git diff failed ({exc}); falling back to full test-all.", file=sys.stderr)
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def match_projects_for_paths(projects: Dict[str, Project], paths: Iterable[str]) -> Set[str]:
    affected: Set[str] = set()
    for changed in paths:
        for name, project in projects.items():
            rel = project.path.relative_to(ROOT).as_posix()
            if changed == rel or changed.startswith(f"{rel}/"):
                affected.add(name)
    return affected


def build_dependents_map(projects: Dict[str, Project]) -> Dict[str, Set[str]]:
    dependents: Dict[str, Set[str]] = {name: set() for name in projects}
    for name, project in projects.items():
        for dep in project.deps:
            if dep in dependents:
                dependents[dep].add(name)
    return dependents


def expand_with_dependents(seed: Set[str], dependents: Dict[str, Set[str]]) -> Set[str]:
    expanded = set(seed)
    queue = list(seed)
    while queue:
        current = queue.pop()
        for dep in dependents.get(current, set()):
            if dep not in expanded:
                expanded.add(dep)
                queue.append(dep)
    return expanded


def run_affected_tests(projects: Dict[str, Project], base_ref: str) -> int:
    changes = changed_files(base_ref)
    if not changes:
        print("[ma] no changes detected; running test-all.")
        return run_all_tests(projects)

    direct = match_projects_for_paths(projects, changes)
    dependents = build_dependents_map(projects)
    affected = expand_with_dependents(direct, dependents)

    if not affected:
        print("[ma] no affected projects matched changed files.")
        return 0

    ordered = [name for name in projects if name in affected and projects[name].tests]
    print(f"[ma] changed files ({len(changes)}):")
    for path in changes:
        print(f"  - {path}")
    print(f"[ma] affected projects: {', '.join(ordered)}")

    failures: List[str] = []
    for name in ordered:
        rc = run_tests_for_project(projects[name])
        if rc != 0:
            failures.append(name)
    if failures:
        print(f"[ma] failed projects: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


def run_project_target(project: Project) -> int:
    if not project.run:
        print(f"[ma] project '{project.name}' has no run command configured.", file=sys.stderr)
        return 1
    return run_subprocess(project.run, cwd=ROOT)


def print_deps(projects: Dict[str, Project], *, reverse: bool = False) -> int:
    dependents = build_dependents_map(projects)
    for name, project in projects.items():
        items = sorted(dependents[name]) if reverse else sorted(project.deps)
        label = "dependents" if reverse else "deps"
        if items:
            print(f"{name} ({project.type}) {label}: {', '.join(items)}")
        else:
            print(f"{name} ({project.type}) {label}: none")
    return 0


def resolve_project_arg(projects: Dict[str, Project], value: str | None, alt: str | None) -> Project:
    name = value or alt
    if not name:
        raise SystemExit("expected a project name (positional or --project)")
    if name not in projects:
        raise SystemExit(f"unknown project '{name}'")
    return projects[name]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Music Advisor pseudo-helper orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-projects", help="List all known projects")

    deps_p = sub.add_parser("deps", help="Show dependency and dependent graph")
    deps_p.add_argument(
        "--reverse",
        action="store_true",
        help="Show dependents instead of dependencies",
    )

    test_p = sub.add_parser("test", help="Run tests for a single project")
    test_p.add_argument("project", nargs="?", help="Project name (see list-projects)")
    test_p.add_argument("--project", dest="project_flag", help="Project name (compatibility)")

    sub.add_parser("test-all", help="Run tests for all projects with configured tests")

    affected_p = sub.add_parser("test-affected", help="Run tests for projects affected by git diff")
    affected_p.add_argument(
        "--base",
        default=os.getenv("MA_AFFECTED_BASE", "origin/main"),
        help="Git ref to diff against (default: origin/main; override with MA_AFFECTED_BASE)",
    )

    run_p = sub.add_parser("run", help="Run a configured project target (if present in registry)")
    run_p.add_argument("project", nargs="?", help="Project name (see list-projects)")
    run_p.add_argument("--project", dest="project_flag", help="Project name (compatibility)")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    projects = load_projects()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-projects":
        return list_projects(projects)

    if args.command == "test":
        project = resolve_project_arg(projects, args.project, getattr(args, "project_flag", None))
        return run_tests_for_project(project)

    if args.command == "deps":
        return print_deps(projects, reverse=getattr(args, "reverse", False))

    if args.command == "test-all":
        return run_all_tests(projects)

    if args.command == "test-affected":
        return run_affected_tests(projects, args.base)

    if args.command == "run":
        project = resolve_project_arg(projects, args.project, getattr(args, "project_flag", None))
        return run_project_target(project)

    parser.error(f"Unhandled command {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
