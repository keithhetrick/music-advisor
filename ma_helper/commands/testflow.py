"""Test, run, affected, and CI-plan command handlers."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from ma_helper.commands.ux import render_error_panel, render_hint_panel
from ma_helper.ui.render import render_task_summary
from ma_helper.core.cache import hash_project, should_skip_cached, update_cache, write_artifact
from ma_helper.core.changes import collect_changes, compute_affected, resolve_base
from ma_helper.core.config import RuntimeConfig
from ma_helper.core.graph import topo_sort
from ma_helper.core.run import _print_summary, record_results, run_projects_parallel, run_projects_serial
from ma_helper.core.state import add_history, guard_level


def _live_table(names, enabled: bool = True):
    """Return (cb, finish) live split-pane helpers using rich if available."""
    if not enabled:
        return None, lambda: None
    try:
        from rich.live import Live
        from rich.table import Table
        from rich.layout import Layout
        from rich.panel import Panel

        state = {name: {"project": name, "rc": None, "duration": 0.0, "cached": False, "last": ""} for name in names}
        logs = []

        def _table():
            tbl = Table(title="ma live (opt-in)", expand=True)
            tbl.add_column("project")
            tbl.add_column("rc")
            tbl.add_column("duration")
            tbl.add_column("cached")
            tbl.add_column("last")
            for name, entry in state.items():
                rc = entry.get("rc")
                rc_txt = "-" if rc is None else ("✅" if rc == 0 else "❌")
                dur = entry.get("duration", 0.0)
                cached = "yes" if entry.get("cached") else ""
                last = entry.get("last", "")
                tbl.add_row(name, rc_txt, f"{dur:.1f}s", cached, last)
            return tbl

        def _layout():
            lay = Layout()
            lay.split_column(Layout(name="tasks"), Layout(name="logs", size=6))
            lay["tasks"].update(_table())
            log_text = "\n".join(logs[-5:]) if logs else "..."
            lay["logs"].update(Panel(log_text, title="recent logs", padding=(0, 1)))
            return lay

        # Use screen=True so the live view stays in-place instead of spamming lines.
        live = Live(_layout(), refresh_per_second=4, screen=True)
        live.start()

        def cb(entry):
            state[entry["project"]] = entry
            if entry.get("last"):
                logs.append(f"{entry['project']}: {entry['last']}")
            live.update(_layout())

        def finish():
            live.update(_layout())
            live.stop()

        return cb, finish
    except Exception:
        return None, lambda: None


def _event_writer(runtime: RuntimeConfig = None) -> Optional[callable]:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import STATE_HOME
        state_home = STATE_HOME
    else:
        state_home = runtime.state_home

    path = os.environ.get("MA_UI_EVENTS")
    if not path:
        path = state_home / "ui_events.ndjson"
    else:
        path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return None

    def cb(entry: Dict[str, object]):
        payload = dict(entry)
        payload["ts"] = time.time()
        try:
            with path.open("a") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass

    return cb


def _combine_cbs(*cbs):
    active = [c for c in cbs if c]

    def cb(entry):
        for fn in active:
            try:
                fn(entry)
            except Exception:
                pass

    finishers = []
    for c in cbs:
        if hasattr(c, "__self__") and hasattr(c.__self__, "stop"):
            finishers.append(c.__self__.stop)
    def finish():
        for fn in finishers:
            try:
                fn()
            except Exception:
                pass
    return cb if active else None, finish


def _render_results(results, title: str):
    """Pretty-print final results table (Rich if available)."""
    render_task_summary(results, title)


def handle_test(args, orch, projects, *, dry_run: bool, log_event, runtime: RuntimeConfig = None) -> int:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root
    proj = orch.resolve_project_arg(projects, args.project, None)
    add_history(f"python tools/ma_orchestrator.py test {proj.name}")
    if dry_run:
        print(f"[ma] dry-run: would run tests for {proj.name}")
        return 0
    missing = [p for p in proj.tests if not (root / p).exists()]
    if missing:
        print(f"[ma] warning: missing test paths for {proj.name}: {', '.join(missing)}", file=sys.stderr)
    skip, info = should_skip_cached(proj, "test", getattr(args, "cache", "off"))
    if skip:
        print(f"[ma] cache hit; skipping {proj.name}")
        return 0
    rc = orch.run_tests_for_project(proj)
    for _ in range(getattr(args, "retries", 0)):
        if rc == 0:
            break
        rc = orch.run_tests_for_project(proj)
    info["hash"] = hash_project(proj)
    update_cache(proj, "test", info, getattr(args, "cache", "off"))
    if getattr(args, "cache", "off") != "off" and rc == 0:
        write_artifact(proj, "test", info)
    record_results([{"project": proj.name, "rc": rc, "duration": 0.0, **info}], "test")
    log_event({"cmd": f"test {proj.name}", "rc": rc})
    return rc


def handle_test_all(args, orch, projects, *, dry_run: bool, log_event, runtime: RuntimeConfig = None) -> int:
    names = topo_sort(projects, [n for n, p in projects.items() if p.tests])
    if dry_run:
        print(f"[ma] dry-run: would run tests for: {', '.join(names)}")
        return 0
    live_enabled = bool(getattr(args, "_live_requested", False) and not getattr(args, "no_live", False))
    live_cb, live_finish = _live_table(names, enabled=live_enabled)
    event_cb = _event_writer(runtime)
    progress_cb, finish = _combine_cbs(live_cb, event_cb)
    if finish is None:
        finish = lambda: None
    if event_cb:
        for n in names:
            event_cb({"project": n, "rc": None, "duration": 0.0, "cached": "", "last": "pending"})
    try:
        if args.parallel and args.parallel > 0:
            rc, results = run_projects_parallel(
                orch, projects, names, args.parallel, getattr(args, "cache", "off"), getattr(args, "retries", 0), progress_cb
            )
            if getattr(args, "json", False):
                print(json.dumps({"label": "test-all", "parallel": True, "results": results, "rc": rc}, indent=2))
            else:
                _render_results(results, "ma_helper run (test-all, parallel)")
        else:
            rc, results = run_projects_serial(
                orch, projects, names, getattr(args, "cache", "off"), getattr(args, "retries", 0), progress_cb
            )
            if getattr(args, "json", False):
                print(json.dumps({"label": "test-all", "parallel": False, "results": results, "rc": rc}, indent=2))
            else:
                _render_results(results, "ma_helper run (test-all)")
    finally:
        finish()
    record_results(results, "test-all")
    log_event({"cmd": "test-all", "rc": rc})
    return rc


def handle_affected(args, orch, projects, *, dry_run: bool, log_event, post_hint, runtime: RuntimeConfig = None) -> int:
    base = resolve_base(args.base, getattr(args, "base_from", None))
    names, changes, mode = compute_affected(
        orch,
        projects,
        base,
        getattr(args, "no_diff", False),
        since=getattr(args, "since", None),
        merge_base=getattr(args, "merge_base", False),
    )
    if not names:
        print("[ma] no affected projects matched changed files.")
        return 0
    if changes:
        print(f"[ma] changed files ({len(changes)}):")
        for path in changes:
            print(f"  - {path}")
    names = topo_sort(projects, names)
    print(f"[ma] affected projects ({mode}): {', '.join(names)}")
    if dry_run:
        print(f"[ma] dry-run: would run tests for: {', '.join(names)}")
        post_hint()
        return 0
    live_enabled = bool(getattr(args, "_live_requested", False) and not getattr(args, "no_live", False))
    live_cb, live_finish = _live_table(names, enabled=live_enabled)
    event_cb = _event_writer(runtime)
    progress_cb, finish = _combine_cbs(live_cb, event_cb)
    if finish is None:
        finish = lambda: None
    if event_cb:
        for n in names:
            event_cb({"project": n, "rc": None, "duration": 0.0, "cached": "", "last": "pending"})
    try:
        if args.parallel and args.parallel > 0:
            rc, results = run_projects_parallel(
                orch, projects, names, args.parallel, getattr(args, "cache", "off"), getattr(args, "retries", 0), progress_cb
            )
            if getattr(args, "json", False):
                print(json.dumps({"label": f"affected-{mode}", "parallel": True, "base": base, "results": results, "rc": rc}, indent=2))
            else:
                _render_results(results, f"affected ({mode}, parallel)")
        else:
            rc, results = run_projects_serial(
                orch, projects, names, getattr(args, "cache", "off"), getattr(args, "retries", 0), progress_cb
            )
            if getattr(args, "json", False):
                print(json.dumps({"label": f"affected-{mode}", "parallel": False, "base": base, "results": results, "rc": rc}, indent=2))
            else:
                _render_results(results, f"affected ({mode})")
    finally:
        finish()
    log_event({"cmd": f"affected --base {base}", "rc": rc})
    record_results(results, f"affected-{mode}")
    post_hint()
    return rc


def handle_run(args, orch, projects, *, dry_run: bool, log_event, require_confirm, runtime: RuntimeConfig = None) -> int:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root
    target = None
    proj_arg = args.project
    if ":" in proj_arg:
        proj_arg, target = proj_arg.split(":", 1)
    proj = orch.resolve_project_arg(projects, proj_arg, None)
    tgt = target or "run"
    if dry_run:
        print(f"[ma] dry-run: would run {tgt} for {proj.name}")
        return 0
    if tgt == "run" and proj.run:
        first = proj.run[0]
        if first.startswith("./") and not (root / first).exists():
            print(f"[ma] warning: run target entry not found: {first}", file=sys.stderr)
            if os.environ.get("MA_REQUIRE_CONFIRM") == "1" or guard_level() == "strict" or os.environ.get("MA_REQUIRE_SAFE_RUN") == "1":
                if not require_confirm(f"Proceed running {proj.name} even though {first} is missing?"):
                    return 1
    if tgt == "run":
        add_history(f"python tools/ma_orchestrator.py run {proj.name}")
        rc = orch.run_project_target(proj)
        log_event({"cmd": f"run {proj.name}", "rc": rc})
        return rc
    if tgt == "test":
        add_history(f"python tools/ma_orchestrator.py test {proj.name}")
        rc = orch.run_tests_for_project(proj)
        log_event({"cmd": f"test {proj.name}", "rc": rc})
        return rc
    print(f"[ma] unknown target '{tgt}' for project '{proj.name}'", file=sys.stderr)
    return 1


def handle_ci_plan(args, orch, projects, runtime: RuntimeConfig = None) -> int:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root

    if os.environ.get("MA_REQUIRE_CLEAN") == "1":
        try:
            res = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True)
            if res.stdout.strip():
                print("[ma] git working tree is dirty; set MA_REQUIRE_CLEAN=0 to bypass.", file=sys.stderr)
                return 1
        except Exception:
            print("[ma] warning: unable to check git status; proceeding.", file=sys.stderr)
    base = resolve_base(args.base, getattr(args, "base_from", None))
    changes = [] if args.no_diff else collect_changes(orch, base, merge_base=getattr(args, "merge_base", False), since=getattr(args, "since", None))
    targets = args.targets

    def emit_matrix(names: List[str]):
        entries = []
        for n in names:
            for t in targets:
                cmd = f"python tools/ma_orchestrator.py test {n}" if t == "test" else f"python tools/ma_orchestrator.py run {n}"
                entries.append({"project": n, "target": t, "cmd": cmd})
        return {"include": entries}

    if changes is None:
        render_error_panel(
            "Unable to compute changes (git diff failed?).",
            [
                "Ensure git is installed and the base ref exists.",
                "Try: ma ci-plan --no-diff to treat all projects as affected.",
                "If using a custom adapter, ensure it sets ROOT and can read git history.",
            ],
        )
        return 1
    if not changes:
        names = [n for n, p in projects.items() if p.tests]
        payload = {"affected": names, "base": base, "note": "no changes or diff unavailable; defaulting to all", "targets": targets}
        if args.commands:
            for name in names:
                for t in targets:
                    cmd = f"python tools/ma_orchestrator.py test {name}" if t == "test" else f"python tools/ma_orchestrator.py run {name}"
                    print(cmd)
            return 0
        if args.matrix or args.gha or args.gitlab or args.circle:
            mat = emit_matrix(names)
            if args.gha:
                gha = {"strategy": {"matrix": mat}, "steps": [{"name": "Run target", "run": "${{ matrix.cmd }}"}]}
                print(json.dumps(gha, indent=2))
            elif args.gitlab:
                print(json.dumps({"parallel": mat}, indent=2))
            elif args.circle:
                print(json.dumps({"parameters": mat}, indent=2))
            else:
                print(json.dumps(mat, indent=2))
            return 0
        try:
            from rich.console import Console
            console = Console()
            console.print_json(data=payload)
        except Exception:
            print(json.dumps(payload, indent=2))
        return 0

    direct = orch.match_projects_for_paths(projects, changes)
    dependents = orch.build_dependents_map(projects)
    affected = orch.expand_with_dependents(direct, dependents)
    names = [n for n in projects if n in affected and projects[n].tests]
    payload = {"base": base, "changes": changes, "affected": names, "targets": targets}
    if args.commands:
        for name in names:
            for t in targets:
                cmd = f"python tools/ma_orchestrator.py test {name}" if t == "test" else f"python tools/ma_orchestrator.py run {name}"
                print(cmd)
        return 0
    if args.matrix or args.gha or args.gitlab or args.circle:
        mat = emit_matrix(names)
        if args.gha:
            gha = {"strategy": {"matrix": mat}, "steps": [{"name": "Run target", "run": "${{ matrix.cmd }}"}]}
            print(json.dumps(gha, indent=2))
        elif args.gitlab:
            print(json.dumps({"parallel": mat}, indent=2))
        elif args.circle:
            print(json.dumps({"parameters": mat}, indent=2))
        else:
            print(json.dumps(mat, indent=2))
        return 0
    try:
        from rich.console import Console
        console = Console()
        console.print_json(data=payload)
    except Exception:
        print(json.dumps(payload, indent=2))
    return 0
