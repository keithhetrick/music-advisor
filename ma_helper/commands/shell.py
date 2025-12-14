"""Interactive shell/REPL for ma_helper."""
from __future__ import annotations

from typing import List

from ma_helper.commands.visual import _dashboard_payload
from ma_helper.core.state import guard_level


def handle_shell(with_dash: bool, interval: float, main_fn) -> int:
    """Simple REPL loop for helper commands. Optionally pin a live dashboard in the same terminal."""
    print("Entering ma_helper shell. Type 'help' to list shortcuts, 'exit' to quit.")
    print("Shortcuts: help, list, tasks, dashboard, map, select, repeat (last), exit.")
    command_palette = {
        "list": "list",
        "tasks": "tasks",
        "dashboard": "dashboard",
        "map": "map",
        "select": "select",
        "test": "test <project>",
        "run": "run <project>[:target]",
        "affected": "affected --base origin/main",
        "verify": "verify",
        "preflight": "preflight",
    }
    last_cmd: List[str] = []
    try:
        from prompt_toolkit import prompt
    except Exception:
        prompt = None  # type: ignore

    dash_live = None
    stop_dash = False
    pause_dash = False

    def print_status():
        try:
            payload = _dashboard_payload()
            git_meta = ""
            if payload.get("git"):
                git_meta = f"branch={payload['git'].get('branch','?')} dirty={payload['git'].get('dirty_count','?')} ahead/behind={payload['git'].get('ahead','?')}/{payload['git'].get('behind','?')}"
            meta = f"types:{', '.join([f'{t}:{c}' for t,c in sorted(payload['types'].items())]) or 'n/a'} | cache:{payload['cache_hit_rate']*100:.1f}% | last_base:{payload.get('last_base','')}"
            last_status = ""
            if payload.get("last", {}).get("results"):
                rows = []
                for r in payload["last"]["results"]:
                    status = "C" if r.get("cached") else ("P" if r.get("rc") == 0 else "F")
                    rows.append(f"{r.get('project')}:{status}/{r.get('duration',0):.2f}s")
                last_status = " last[" + "; ".join(rows) + "]"
            print(f"[ma status] {meta} | git[{git_meta or 'n/a'}]{last_status}")
        except Exception:
            pass

    if with_dash:
        print(f"[ma] Status updates enabled; refreshed after each command (interval hint: {interval}s).")
        print_status()

    while True:
        try:
            if dash_live:
                pause_dash = True
            if prompt:
                line = prompt("ma> ").strip()
            else:
                line = input("ma> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            stop_dash = True
            if dash_live:
                dash_live.join(timeout=1)
            return 0
        finally:
            if dash_live:
                pause_dash = False
        if not line:
            continue
        if line in ("exit", "quit"):
            print("Bye.")
            stop_dash = True
            if dash_live:
                dash_live.join(timeout=1)
            return 0
        if line == "help":
            print("Shortcuts: list, tasks, dashboard, map, select, test <proj>, run <proj>, affected --base origin/main, verify, repeat (last), exit.")
            print("Palette:")
            for name, val in command_palette.items():
                print(f" - {name}: {val}")
            continue
        if line == "repeat":
            if not last_cmd:
                print("[ma] no previous command.")
                continue
            line = " ".join(last_cmd)
        tokens = line.split()
        try:
            last_cmd = tokens
            main_fn(tokens)
        except SystemExit:
            # avoid exiting the shell
            pass
        finally:
            if with_dash:
                print_status()
    return 0
