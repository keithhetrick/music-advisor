"""Dashboard/TUI renderers."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from ma_helper.core.config import RuntimeConfig
from ma_helper.core.registry import load_registry


def _dashboard_payload(runtime: RuntimeConfig = None) -> Dict[str, Any]:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import LAST_RESULTS_FILE, ROOT
        last_results_file, root = LAST_RESULTS_FILE, ROOT
    else:
        last_results_file, root = runtime.last_results_file, runtime.root
    reg = load_registry()
    total = len(reg)
    engine = len([1 for _, m in reg.items() if m.get("type") == "engine"])
    shared = len([1 for _, m in reg.items() if m.get("type") == "shared"])
    hosts = len([1 for _, m in reg.items() if m.get("type") == "host" or m.get("type") == "host_core"])
    misc = total - engine - shared - hosts
    last_results = {}
    if last_results_file.exists():
        try:
            last_results = json.loads(last_results_file.read_text())
        except Exception:
            last_results = {}
    git_meta = {}
    try:
        import subprocess

        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True)
        git_meta = {"branch": branch, "dirty": bool(dirty.strip())}
    except Exception:
        pass
    return {
        "counts": {"total": total, "engine": engine, "shared": shared, "hosts": hosts, "misc": misc},
        "types": {"engine": engine, "shared": shared, "hosts": hosts, "misc": misc},
        "last": last_results,
        "git": git_meta,
    }


def render_dashboard(*, as_json=False, as_html=False, live=False, interval=1.0, duration=0.0, runtime: RuntimeConfig = None) -> int:
    payload = _dashboard_payload(runtime)
    if as_json:
        print(json.dumps(payload, indent=2))
        return 0
    if as_html:
        html = f"<pre>{json.dumps(payload, indent=2)}</pre>"
        print(html)
        return 0
    if live:
        try:
            from rich.console import Console
            from rich.live import Live
            from rich.panel import Panel
            from time import sleep

            console = Console()
            start = time.time()
            with Live(refresh_per_second=1, console=console) as live:
                while True:
                    payload = _dashboard_payload(runtime)
                    live.update(Panel(json.dumps(payload, indent=2), title="Dashboard"))
                    if duration and (time.time() - start) > duration:
                        break
                    sleep(interval)
        except Exception:
            # fallback
            while True:
                print(json.dumps(_dashboard_payload(runtime), indent=2))
                if duration:
                    time.sleep(duration)
                    break
                time.sleep(interval)
        return 0
    # default summary
    counts = payload["counts"]
    print(f"Projects: total {counts['total']} | engines {counts['engine']} | shared {counts['shared']} | hosts {counts['hosts']} | misc {counts['misc']}")
    last = payload.get("last", {})
    if last:
        print(f"Last run: {last.get('label','')} at {last.get('ts','')}")
        for r in last.get("results", []):
            status = "cached" if r.get("cached") else ("ok" if r.get("rc") == 0 else "fail")
            print(f"- {r.get('project')}: {status} ({r.get('duration',0):.2f}s)")
    return 0


def render_tui(interval: float, duration: int) -> int:
    try:
        from ma_helper.ui.dashboard import render_live_dashboard
        return render_live_dashboard(interval=interval, duration=duration)
    except Exception:
        print("[ma] tui requires rich; falling back to dashboard --json.")
        return render_dashboard(as_json=True)
