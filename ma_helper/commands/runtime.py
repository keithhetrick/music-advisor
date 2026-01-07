"""Runtime-oriented commands: watch, shell, tui/dashboard wrappers."""
from __future__ import annotations

import os
import subprocess
import time

from ma_helper.core.config import RuntimeConfig
from ma_helper.core.state import add_history, guard_level


def handle_watch(args, orch, *, dry_run: bool, require_confirm) -> int:
    from ma_helper.commands.watch import run_watch_loop

    base_cmd = args.cmd or f"python3 tools/ma_orchestrator.py test {args.project}"
    return run_watch_loop(args, orch, base_cmd, dry_run=dry_run, require_confirm=require_confirm)


def handle_shell(args, main_fn) -> int:
    return main_fn()


def handle_tui(args) -> int:
    from ma_helper.commands.visual import render_tui

    return render_tui(args.interval, args.duration)


def handle_dashboard(args, runtime: RuntimeConfig = None) -> int:
    from ma_helper.commands.visual import render_dashboard

    return render_dashboard(
        as_json=getattr(args, "json", False),
        as_html=getattr(args, "html", False),
        live=getattr(args, "live", False),
        interval=getattr(args, "interval", 1.0),
        duration=getattr(args, "duration", 0.0),
        runtime=runtime,
    )


def handle_sparse(args, require_confirm, run_cmd, runtime: RuntimeConfig = None) -> int:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root

    if args.list:
        return run_cmd("git sparse-checkout list", cwd=root)
    if args.reset:
        if not require_confirm("Disable sparse-checkout?"):
            print("[ma] aborting (strict guard).")
            return 1
        return run_cmd("git sparse-checkout disable", cwd=root)
    if args.set:
        paths = args.set
        print(f"[ma] enabling cone mode and setting paths: {paths}")
        rc = run_cmd("git sparse-checkout init --cone", cwd=root)
        if rc != 0:
            return rc
        return run_cmd("git sparse-checkout set " + " ".join(paths), cwd=root)
    print("Usage: sparse --list | --reset | --set <paths...>")
    return 1


def handle_watch_cli(args, orch, *, dry_run: bool, require_confirm):
    return handle_watch(args, orch, dry_run=dry_run, require_confirm=require_confirm)


def handle_shell_cli(args, main_fn):
    return handle_shell(args, main_fn)


def handle_tui_cli(args):
    return handle_tui(args)
