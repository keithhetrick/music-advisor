"""Tooling helpers: lint, typecheck, format, verify, CI env, rerun, history."""
from __future__ import annotations

import json
import subprocess
import time
from typing import Any, Dict, List

from ma_helper.core.env import ROOT
from ma_helper.core.state import load_favorites
from ma_helper.commands.smoke import run_smoke


def run_lint() -> int:
    cmd = "./infra/scripts/with_repo_env.sh -m ruff check hosts/advisor_host engines/recommendation_engine/recommendation_engine"
    return subprocess.call(cmd, shell=True, cwd=ROOT)


def run_typecheck() -> int:
    cmd = "./infra/scripts/with_repo_env.sh -m mypy --config-file hosts/advisor_host/pyproject.toml hosts/advisor_host"
    return subprocess.call(cmd, shell=True, cwd=ROOT)


def run_format() -> int:
    cmd = "./infra/scripts/with_repo_env.sh -m ruff format hosts/advisor_host engines/recommendation_engine/recommendation_engine"
    return subprocess.call(cmd, shell=True, cwd=ROOT)


def handle_verify(args, run_affected, post_hint) -> int:
    steps = [
        ("lint", run_lint),
        ("typecheck", run_typecheck),
        ("smoke pipeline", lambda: run_smoke("pipeline")),
        ("affected", lambda: run_affected()),
    ]
    if getattr(args, "dry_run", False):
        print("[ma] dry-run: verify would run -> " + ", ".join(name for name, _ in steps))
        post_hint()
        return 0

    try:
        from rich.live import Live
        from rich.table import Table

        state = {name: {"rc": None, "duration": 0.0} for name, _ in steps}

        def _table():
            tbl = Table(title="verify", expand=True)
            tbl.add_column("step")
            tbl.add_column("rc")
            tbl.add_column("duration")
            for name, vals in state.items():
                rc = vals["rc"]
                rc_txt = "-" if rc is None else ("✅" if rc == 0 else "❌")
                tbl.add_row(name, rc_txt, f"{vals['duration']:.1f}s")
            return tbl

        live = Live(_table(), refresh_per_second=4)
        live.start()
        try:
            for label, fn in steps:
                start = time.time()
                live.update(_table())
                rc = fn()
                state[label]["rc"] = rc
                state[label]["duration"] = time.time() - start
                live.update(_table())
                if rc != 0 and not args.ignore_failures:
                    return rc
        finally:
            live.update(_table())
            live.stop()
    except Exception:
        for label, fn in steps:
            print(f"[ma] verify -> {label}")
            rc = fn()
            if rc != 0 and not args.ignore_failures:
                return rc
    post_hint()
    return 0


def handle_ci_env() -> int:
    envs = {
        "AWS_PROFILE": "Set if using AWS CLI creds",
        "MA_HELPER_HOME": "Optional override for helper cache/state (default ~/.ma_helper)",
        "MA_REQUIRE_PREFLIGHT": "1 to force preflight before test commands",
        "MA_REQUIRE_CLEAN": "1 to fail if git tree dirty for critical commands",
    }
    for k, v in envs.items():
        print(f"{k} : {v}")
    return 0


def handle_rerun_last(load_favs, run_cmd) -> int:
    data = load_favs()
    last = data.get("last_failed")
    if not last:
        print("[ma] no last failed command recorded.")
        return 0
    print(f"[ma] rerunning last failed: {last}")
    return run_cmd(last)


def handle_history(load_favs, limit: int) -> int:
    data = load_favs()
    hist = data.get("history", [])[-limit:]
    if not hist:
        print("[ma] no history yet.")
        return 0
    print("Recent history:")
    for h in hist:
        print(f"- {h}")
    return 0
