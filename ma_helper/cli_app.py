#!/usr/bin/env python3
"""
Friendly wrapper CLI for the Music Advisor monorepo.

This is a thin layer over tools/ma_orchestrator.py to mimic the UX of Nx/Turborepo:
- Single entrypoint: `ma` (console script) or `python -m ma_helper` or `python tools/ma.py`
- Interactive picker: `ma select`
- Quick task list: `ma tasks`
- Watch loop (entr/watchfiles): `ma watch audio_engine`
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from functools import partial
from pathlib import Path
from typing import Any, Dict, List

from ma_helper.commands import handle_affected, handle_ci_plan, handle_run, handle_test, handle_test_all
from ma_helper.adapters import get_adapter as get_orch_adapter
from ma_helper.commands.dispatch import log_event as base_log_event
from ma_helper.commands.dispatch import require_confirm
from ma_helper.commands.dispatch import run_cmd as base_run_cmd
from ma_helper.commands.favorites import handle_cache, handle_favorites, handle_logs
from ma_helper.commands.gitflow import handle_hook, handle_precommit
from ma_helper.commands.gitops import handle_git_branch, handle_git_pull_check, handle_git_rebase, handle_git_status, handle_git_upstream
from ma_helper.commands.chatdev import handle_chat_dev
from ma_helper.commands.helpdesk import (
    handle_completion,
    handle_help,
    handle_info,
    handle_map,
    handle_playbook,
    handle_profile,
    handle_select,
    handle_tasks,
    handle_tour,
    handle_welcome,
    maybe_advance_tour,
)
from ma_helper.commands.parser import build_parser
from ma_helper.commands.registry_cmds import handle_registry
from ma_helper.commands.runtime import handle_dashboard, handle_shell_cli, handle_sparse, handle_tui_cli, handle_watch_cli
from ma_helper.commands.dashboard import run_dashboard
from ma_helper.commands.scaffold import handle_scaffold
from ma_helper.commands.shell import handle_shell
from ma_helper.commands.smoke import run_smoke
from ma_helper.commands.taskgraph import handle_tasks_run
from ma_helper.commands.ux import prompt_if_missing
from ma_helper.commands.system import handle_check, handle_doctor, handle_guard, handle_preflight
from ma_helper.commands.system_ops import run_github_check
from ma_helper.commands.tooling import handle_ci_env, handle_history, handle_rerun_last, run_format, run_lint, run_typecheck, handle_cache
from ma_helper.commands.graph_cmds import handle_graph
from ma_helper.commands.verify import run_verify
from ma_helper.commands.ux import maybe_first_run_hint, post_affected_hint, post_list_hint, post_verify_hint, show_world, render_header, live_header
from ma_helper.commands.visual import _dashboard_payload
from ma_helper.core import env
from ma_helper.core.config import HelperConfig, RuntimeConfig
from ma_helper.core.root import discover_root
from ma_helper.core.git import enforce_clean_tree, enforce_permissions, git_summary
from ma_helper.core.graph import emit_graph
from ma_helper.core.python import resolve_python
from ma_helper.core.state import add_history, guard_level, load_favorites, save_favorites, set_last_failed
from ma_helper.policy import permission_level, require_unlock

DRY_RUN = False

# Config / adapters
ROOT_ACTUAL = discover_root(env.ROOT)
config = HelperConfig.load(ROOT_ACTUAL)
env.apply_config(config)
adapter_factory = get_orch_adapter(config.adapter)
orch_adapter = adapter_factory(config.root)

# Friendly task aliases (overrideable via config)
TASKS: Dict[str, str] = {}
log_event = partial(base_log_event, load_favorites, env.TELEMETRY_FILE)
_run_cmd = partial(base_run_cmd, orch_root=config.root, log_event_fn=log_event, set_last_failed=set_last_failed)


def cmd_dashboard() -> int:
    return run_dashboard(
        as_json=getattr(cmd_dashboard, "as_json", False),
        as_html=getattr(cmd_dashboard, "as_html", False),
        live=getattr(cmd_dashboard, "live", False),
        interval=getattr(cmd_dashboard, "interval", 1.0),
        duration=getattr(cmd_dashboard, "duration", 0.0),
    )
def cmd_shell(with_dash: bool = False, interval: float = 1.0) -> int:
    return handle_shell(with_dash, interval, main)
def main(argv=None) -> int:
    start_time = time.time()
    raw = list(argv) if argv is not None else sys.argv[1:]
    # Track presence of --live explicitly so defaults stay off unless requested.
    live_requested = "--live" in raw
    # Allow --header/--header-live even after the subcommand by stripping first.
    header_flag = False
    header_live_flag = False
    filtered = []
    for tok in raw:
        if tok == "--header":
            header_flag = True
            continue
        if tok == "--header-live":
            header_live_flag = True
            continue
        filtered.append(tok)
    args = build_parser().parse_args(filtered)
    # Re-apply global flags if they were passed after the subcommand
    if header_flag:
        setattr(args, "header", True)
    if header_live_flag:
        setattr(args, "header_live", True)

    # Create immutable runtime config (replaces global config/orch_adapter mutations)
    root = Path(args.root).resolve() if getattr(args, "root", None) else ROOT_ACTUAL
    helper_config = HelperConfig.load(root)
    runtime = RuntimeConfig.from_helper_config(helper_config)

    # Create adapter from runtime config
    adapter_factory = get_orch_adapter(helper_config.adapter)
    orch_adapter = adapter_factory(runtime.root)

    # Temporary: also update legacy globals for consumers not yet migrated
    env.apply_config(helper_config)
    # Persist whether the user explicitly asked for --live (defaults stay off).
    setattr(args, "_live_requested", live_requested)

    # Handle telemetry file override
    telemetry_file = runtime.telemetry_file
    if getattr(args, "telemetry_file", None):
        telemetry_file = Path(args.telemetry_file).resolve()
        env.TELEMETRY_FILE = telemetry_file  # Also update legacy global

    telemetry_enabled = not getattr(args, "no_telemetry", False) and telemetry_file is not None
    log_event = partial(base_log_event, load_favorites, telemetry_file if telemetry_enabled else None)
    _run_cmd = partial(
        base_run_cmd,
        orch_root=runtime.root,
        log_event_fn=log_event if telemetry_enabled else None,
        set_last_failed=set_last_failed,
    )
    # Global banner for most commands (skip the ones that already print rich banners)
    banner_skips = {"palette", "quickstart", "welcome", "tour", "help"}
    header_live_ctx = None
    live_update_fn = None
    heavy_no_live_header = {"test-all", "affected", "verify"}
    if getattr(args, "header_live", False) and args.command in heavy_no_live_header:
        setattr(args, "header_live", False)
        # fall back to single header if requested
        if header_flag:
            render_header()
    if args.command not in banner_skips:
        if getattr(args, "header_live", False):
            def _status_text():
                summary = git_summary()
                guard = guard_level()
                branch = summary.get("branch", "?")
                dirty = summary.get("dirty", "?")
                ahead = summary.get("ahead", "?")
                behind = summary.get("behind", "?")
                cmd = args.command
                git_mode = os.environ.get("MA_GIT_MODE", "on")
                return f"[bold cyan]Music Advisor[/] | cmd: {cmd} | branch: {branch} | dirty: {dirty} | ahead/behind: {ahead}/{behind} | guard: {guard} | git: {git_mode}"
            header_live_ctx = live_header(_status_text)
        elif getattr(args, "header", False):
            render_header()
        else:
            show_world(args.command)
    if args.command not in {"palette", "quickstart", "welcome", "tour"}:
        maybe_first_run_hint(args.command, save_favorites, load_favorites)
    if telemetry_enabled and telemetry_file:
        print(f"[ma] telemetry → {telemetry_file}")
    projects = orch_adapter.load_projects()
    dry_run = getattr(args, "dry_run", False)
    enforce_permissions(runtime.root)  # warn-only
    must_clean = {"test", "test-all", "affected", "run", "watch", "verify", "ci-plan"}
    if args.command in must_clean:
        if not enforce_clean_tree():
            return 1

    # Global guard: optionally enforce preflight before certain commands
    must_preflight = {"test", "test-all", "affected", "verify", "watch"}
    env_require_preflight = os.environ.get("MA_REQUIRE_PREFLIGHT") == "1"
    if (getattr(args, "require_preflight", False) or env_require_preflight) and args.command in must_preflight:
        if cmd_preflight() != 0:
            print("[ma] preflight failed; aborting as requested.")
            return 1

    rc = None
    if getattr(args, "header_live", False) and header_live_ctx:
        with header_live_ctx as update_fn:
            live_update_fn = update_fn
            rc = _dispatch(args, runtime, helper_config, orch_adapter, projects, dry_run, log_event, require_confirm, status_update=live_update_fn)
    else:
        rc = _dispatch(args, runtime, helper_config, orch_adapter, projects, dry_run, log_event, require_confirm, status_update=live_update_fn)
    if telemetry_enabled and log_event:
        try:
            log_event({"cmd": args.command, "rc": rc, "duration_sec": round(time.time() - start_time, 3)})
        except Exception:
            pass
    if rc == 0:
        try:
            maybe_advance_tour(args.command)
        except Exception:
            pass
    return rc


def _dispatch(args, runtime: RuntimeConfig, helper_config: HelperConfig, orch_adapter, projects, dry_run, log_event, require_confirm, status_update=None):
    py_bin = resolve_python(runtime)
    if args.command == "list":
        rc = orch_adapter.list_projects(projects)
        post_list_hint()
        return rc
    if args.command == "tasks":
        aliases = helper_config.task_aliases or TASKS
        return handle_tasks(aliases, getattr(args, "filter", None), getattr(args, "json", False))
    if args.command == "test":
        rc = handle_test(args, orch_adapter, projects, dry_run=dry_run, log_event=log_event, runtime=runtime)
        if rc != 0:
            from ma_helper.commands.ux import render_error_panel, render_hint_panel
            render_error_panel(f"Tests failed for {args.project}", ["Re-run failed: ma rerun-last", "Run doctor: ma doctor --check-tests"])
            render_hint_panel("Next", ["ma affected --base origin/main", "ma dashboard --json"])
        return rc
    if args.command == "test-all":
        rc = handle_test_all(args, orch_adapter, projects, dry_run=dry_run, log_event=log_event, runtime=runtime)
        if rc != 0:
            from ma_helper.commands.ux import render_error_panel
            render_error_panel("test-all failed", ["Re-run: ma test-all", "Inspect last results: tail -n 20 ~/.ma_helper/last_results.json"])
        return rc
    if args.command == "affected":
        rc = handle_affected(args, orch_adapter, projects, dry_run=dry_run, log_event=log_event, post_hint=post_affected_hint, runtime=runtime)
        if rc != 0:
            from ma_helper.commands.ux import render_error_panel
            render_error_panel("affected failed", ["Retry with --no-diff if needed", "Check git status for untracked changes"])
        return rc
    if args.command == "run":
        if not require_unlock("write", args, require_confirm=require_confirm):
            return 1
        return handle_run(args, orch_adapter, projects, dry_run=dry_run, log_event=log_event, require_confirm=require_confirm, runtime=runtime)
    if args.command == "deps":
        if args.graph and args.graph != "text":
            return emit_graph(projects, args.graph)
        return orch_adapter.print_deps(projects, reverse=getattr(args, "reverse", False))
    if args.command == "select":
        return handle_select(projects, runtime)
    if args.command == "watch":
        return handle_watch_cli(args, orch_adapter, dry_run=dry_run, require_confirm=require_confirm)
    if args.command == "ci-plan":
        return handle_ci_plan(args, orch_adapter, projects, runtime)
    if args.command == "favorites":
        return handle_favorites(args, runtime)
    if args.command == "doctor":
        return handle_doctor(getattr(args, "require_optional", False), getattr(args, "interactive", False), getattr(args, "check_tests", False), projects, runtime)
    if args.command == "guard":
        return handle_guard(args)
    if args.command == "check":
        return handle_check()
    if args.command == "preflight":
        return handle_preflight(orch_adapter, runtime)
    if args.command == "github-check":
        return run_github_check(
            args,
            require_confirm=require_confirm,
            cmd_verify=lambda ns: run_verify(ns, lambda: main(["affected", "--no-diff"]), post_verify_hint),
            orch=orch_adapter,
        )
    if args.command == "hook":
        return handle_hook(args, runtime)
    if args.command == "precommit":
        return handle_precommit(args, runtime)
    if args.command == "sparse":
        runner = _run_cmd
        if status_update:
            runner = partial(base_run_cmd, orch_root=runtime.root, log_event_fn=log_event, set_last_failed=set_last_failed, status_update=status_update)
        return handle_sparse(args, require_confirm, runner, runtime)
    if args.command == "scaffold":
        return handle_scaffold(args, runtime)
    if args.command == "smoke":
        return run_smoke(Path(args.audio).expanduser().resolve(), py_bin, runtime)
    if args.command == "verify":
        return run_verify(args, lambda: main(["affected", "--no-diff"]), post_verify_hint)
    if args.command == "ci-env":
        return handle_ci_env()
    if args.command == "lint":
        return run_lint()
    if args.command == "typecheck":
        return run_typecheck()
    if args.command == "format":
        return run_format()
    if args.command == "rerun-last":
        runner = _run_cmd
        if status_update:
            runner = partial(base_run_cmd, orch_root=runtime.root, log_event_fn=log_event, set_last_failed=set_last_failed, status_update=status_update)
        return handle_rerun_last(load_favorites, lambda cmd: runner(cmd, cwd=runtime.root))
    if args.command == "welcome":
        return handle_welcome()
    if args.command == "help":
        return handle_help({"list": "list projects", "tasks": "task aliases", "affected": "run changed tests"})
    if args.command == "quickstart":
        from ma_helper.commands.info import handle_quickstart
        return handle_quickstart(None)
    if args.command == "palette":
        from ma_helper.commands.info import handle_palette
        return handle_palette(None)
    if args.command == "history":
        return handle_history(load_favorites, args.limit)
    if args.command == "info":
        return handle_info(args.project)
    if args.command == "playbook":
        return handle_playbook(args.name, args.dry_run, runtime)
    if args.command == "registry":
        return handle_registry(args, helper_config.registry_path, runtime)
    if args.command == "tasks-run":
        return handle_tasks_run(args, _run_cmd, log_event)
    if args.command == "map":
        if args.format == "svg" and args.open:
            emit_graph.open_svg = True
        return handle_map(args.format, args.filter, args.open)
    if args.command == "graph":
        return handle_graph(getattr(args, "format", "ansi"), getattr(args, "filter", None))
    if args.command == "dashboard":
        cmd_dashboard.as_json = getattr(args, "json", False)
        cmd_dashboard.as_html = getattr(args, "html", False)
        cmd_dashboard.live = getattr(args, "live", False)
        cmd_dashboard.interval = getattr(args, "interval", 1.0)
        cmd_dashboard.duration = getattr(args, "duration", 0.0)
        return handle_dashboard(args, runtime)
    if args.command == "tui":
        return handle_tui_cli(args)
    if args.command == "ui":
        try:
            try:
                from ma_helper.tui.app import HelperTUI
            except Exception:
                print("[ma] textual is not installed; install with: python3 -m pip install 'textual>=0.55'")
                return 1
            reg = orch_adapter.load_projects()
            results_path = Path(args.results) if getattr(args, "results", None) else runtime.last_results_file
            log_path = Path(args.logs) if getattr(args, "logs", None) else runtime.log_file
            app = HelperTUI(list(reg.keys()), results_path=results_path, log_path=log_path, interval=getattr(args, "interval", 1.0), state_home=runtime.state_home)
            app.run()
            return 0
        except Exception as exc:
            print(f"[ma] TUI failed: {exc}")
            return 1
    if args.command == "tour":
        return handle_tour(getattr(args, "reset", False), getattr(args, "advance", False), runtime)
    if args.command == "logs":
        return handle_logs(args, runtime.log_file)
    if args.command == "profile":
        return handle_profile(args, runtime)
    if args.command == "cache":
        return handle_cache(args, runtime)
    if args.command == "shell":
        return handle_shell_cli(args, lambda: cmd_shell(with_dash=getattr(args, "dash", False), interval=getattr(args, "interval", 1.0)))
    if args.command == "completion":
        return handle_completion(args.shell, build_parser)
    if args.command == "git-branch":
        if not getattr(args, "project", None):
            args.project = prompt_if_missing("project", None, "Project for branch name: ")
        return handle_git_branch(args)
    if args.command == "chat-dev":
        return handle_chat_dev(args, runtime)
    if args.command == "git-status":
        return handle_git_status(args)
    if args.command == "git-upstream":
        return handle_git_upstream(args)
    if args.command == "git-rebase":
        return handle_git_rebase(args)
    if args.command == "git-pull-check":
        return handle_git_pull_check(args)

    print(f"Unknown command {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
