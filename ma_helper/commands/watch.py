"""Watch loop handler (entr/watchfiles)."""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from typing import Any

from ma_helper.core.env import ROOT
from ma_helper.core.state import load_favorites, set_last_failed, add_history, guard_level


def run_watch_loop(args, orch, base_cmd: str, *, dry_run: bool, require_confirm) -> int:
    project_name = args.project
    projects = orch.load_projects()
    if project_name not in projects:
        print(f"[ma] unknown project '{project_name}'.", file=os.sys.stderr)
        return 1
    project = projects[project_name]
    if not project.path.exists():
        print(f"[ma] project path does not exist: {project.path}", file=os.sys.stderr)
        return 1
    if guard_level() == "strict":
        if not require_confirm(f"Start watch on {project_name}?"):
            print("[ma] aborted (strict guard).")
            return 1
    add_history(f"watch {project_name}: {base_cmd}")
    # capture optional hooks
    on_success = getattr(args, "on_success", None)
    on_fail = getattr(args, "on_fail", None)
    preset = getattr(args, "preset", None)
    if preset == "test":
        base_cmd = f"python3 tools/ma_orchestrator.py test {project_name}"
    if preset == "lint":
        base_cmd = "./infra/scripts/with_repo_env.sh -m ruff check hosts/advisor_host engines/recommendation_engine/recommendation_engine"
    rerun_failed = getattr(args, "rerun_last_failed", False)
    if rerun_failed:
        data = load_favorites()
        last_failed = data.get("last_failed")
        if last_failed:
            print(f"[ma] rerunning last failed command before watch: {last_failed}")
            _run_cmd(last_failed, cwd=orch.ROOT)
    hotkeys = getattr(args, "hotkeys", False)
    use_hotkeys = hotkeys
    if dry_run:
        print(f"[ma] dry-run: would watch {project_name} with cmd: {base_cmd}")
        return 0
    if shutil.which("entr"):
        if use_hotkeys:
            print("[ma] hotkeys not supported with entr; falling back to normal watch.")
            use_hotkeys = False
        cmd = f"find {project.path} -type f | entr -r {base_cmd}"
        print(f"[ma] watching {project.path} with entr -> {base_cmd}")
        rc = subprocess.call(["bash", "-lc", cmd], cwd=orch.ROOT)
        if rc == 0 and on_success:
            _run_cmd(on_success, cwd=orch.ROOT)
        if rc != 0 and on_fail:
            _run_cmd(on_fail, cwd=orch.ROOT)
        return rc
    try:
        from watchfiles import awatch  # type: ignore
    except Exception:
        print("[ma] install `entr` or `watchfiles` to use watch (pip install watchfiles).", file=os.sys.stderr)
        return 1

    async def _loop():
        print(f"[ma] watching {project.path} with watchfiles -> {base_cmd}")
        if use_hotkeys:
            print("[ma] hotkeys: r=rerun, f=last failed (if any), q=quit")
        last_failed_cmd = load_favorites().get("last_failed")
        async for _ in awatch(project.path):
            rc = _run_cmd(base_cmd, cwd=orch.ROOT)
            if rc != 0:
                print(f"[ma] command exited {rc}; continuing watch.")
                if on_fail:
                    _run_cmd(on_fail, cwd=orch.ROOT)
                set_last_failed(base_cmd)
            else:
                if on_success:
                    _run_cmd(on_success, cwd=orch.ROOT)
            if use_hotkeys:
                try:
                    import sys, select
                    print("[ma] (hotkeys) press r=re-run, f=last failed, q=quit (waiting 1s)...")
                    i, _, _ = select.select([sys.stdin], [], [], 1)
                    if i:
                        key = sys.stdin.readline().strip().lower()
                        if key == "q":
                            print("[ma] watch exiting (q).")
                            return
                        if key == "r":
                            print("[ma] hotkey rerun")
                            _run_cmd(base_cmd, cwd=orch.ROOT)
                        if key == "f" and last_failed_cmd:
                            print("[ma] hotkey rerun last failed")
                            _run_cmd(last_failed_cmd, cwd=orch.ROOT)
                except Exception:
                    pass

    return asyncio.run(_loop())


def _run_cmd(cmd: str, *, cwd=None) -> int:
    print(f"[ma] {cmd}")
    return subprocess.call(cmd, shell=True, cwd=cwd or ROOT)
