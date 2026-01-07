"""Help/welcome/tour/completion/tasks/select/info/profile/playbook/map helpers."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List

from ma_helper.core.config import RuntimeConfig
from ma_helper.core.registry import filter_projects, load_registry
from ma_helper.core.state import guard_level
from ma_helper.commands.ux import print_ma_banner, show_world


def handle_tasks(tasks: Dict[str, str], filter_substr: str | None = None, as_json: bool = False) -> int:
    items = [(name, cmd) for name, cmd in tasks.items() if not filter_substr or filter_substr in name or filter_substr in cmd]
    if as_json:
        print(json.dumps([{"name": n, "cmd": c} for n, c in items], indent=2))
        return 0
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Common tasks", show_header=True, header_style="bold cyan")
        table.add_column("name")
        table.add_column("command")
        for name, cmd in items:
            table.add_row(name, cmd)
        console.print(table)
        console.print("[dim]Tip: you can also run Makefile/Taskfile targets directly (make/task).[/]")
        return 0
    except Exception:
        print("Common tasks:")
        for name, cmd in items:
            print(f"- {name}: {cmd}")
        print("\nTip: you can also run Makefile/Taskfile targets directly (make/task).")
        return 0


def handle_select(projects, runtime: RuntimeConfig = None) -> int:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root
    choices = sorted(projects.keys())
    print("Select a project (blank to exit):")
    for idx, name in enumerate(choices, 1):
        proj = projects[name]
        print(f"{idx}. {name:<22} [{proj.type}] - {proj.path}")
    try:
        sel = input("Enter number (or blank to cancel): ").strip()
    except Exception:
        return 1
    if not sel:
        return 0
    try:
        idx = int(sel)
    except ValueError:
        print("[ma] invalid selection.")
        return 1
    if idx < 1 or idx > len(choices):
        print("[ma] out of range.")
        return 1
    name = choices[idx - 1]
    proj = projects[name]
    # simple follow-up menu
    print(f"[ma] selected {name}. Choose action:")
    actions = ["test", "run", "deps", "affected", "watch"]
    for i, act in enumerate(actions, 1):
        print(f"{i}. {act}")
    try:
        sel2 = input("Enter number: ").strip()
    except Exception:
        return 1
    try:
        act = actions[int(sel2) - 1]
    except Exception:
        print("[ma] invalid action.")
        return 1
    if act == "test":
        return subprocess.call(f"python tools/ma_orchestrator.py test {name}", shell=True, cwd=root)
    if act == "run":
        return subprocess.call(f"python tools/ma_orchestrator.py run {name}", shell=True, cwd=root)
    if act == "deps":
        return subprocess.call(f"python -m ma_helper deps {name}", shell=True, cwd=root)
    if act == "affected":
        return subprocess.call("python -m ma_helper affected --base origin/main", shell=True, cwd=root)
    if act == "watch":
        return subprocess.call(f"python -m ma_helper watch {name}", shell=True, cwd=root)
    return 0


def handle_welcome() -> int:
    show_world("welcome")
    print("Welcome to the Music Advisor helper.")
    print("Try: ma quickstart | ma palette | ma list | ma affected --base origin/main")
    print("Docs: docs/tools/helper_cli.md")
    return 0


def handle_help(palette: Dict[str, str]) -> int:
    print_ma_banner()
    print("Helper commands:")
    for k, v in palette.items():
        print(f"- {k:<14} {v}")
    print("\nGit helpers:")
    git_cmds = {
        "git-status": "branch/dirty/ahead-behind (+ --branches to list recent)",
        "git-branch": "create a feature branch (namespaced, optional sparse)",
        "git-upstream": "set upstream for current branch",
        "git-rebase": "rebase onto target (default origin/main)",
        "git-pull-check": "pull only if clean tree",
        "github-check": "pre-push/pre-CI gate (clean, upstream, preflight, verify)",
        "sparse": "git sparse-checkout helpers",
        "hook": "install pre-push hook",
        "precommit": "print/install pre-commit hook",
    }
    for k, v in git_cmds.items():
        print(f"- {k:<14} {v}")
    print("\nTasks/graph:")
    task_cmds = {
        "tasks-run": "run tasks from ma_helper.toml with deps/outputs (Nx-style)",
    }
    for k, v in task_cmds.items():
        print(f"- {k:<14} {v}")
    print("\nTip: ma palette | ma quickstart | ma list")
    return 0


def handle_info(project: str) -> int:
    reg = load_registry()
    meta = reg.get(project)
    if not meta:
        print(f"[ma] project '{project}' not found in registry.", file=sys.stderr)
        return 1
    print(json.dumps(meta, indent=2))
    return 0


def handle_playbook(name: str, dry_run: bool, runtime: RuntimeConfig = None) -> int:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root
    scripts = {
        "pipeline-dev": ["python tools/ma_orchestrator.py test-all"],
        "host-dev": ["python tools/ma_orchestrator.py run advisor_host"],
        "sidecar-dev": ["python tools/ma_orchestrator.py run audio_engine"],
    }
    cmds = scripts.get(name, [])
    if not cmds:
        print(f"[ma] unknown playbook {name}")
        return 1
    for cmd in cmds:
        if dry_run:
            print(f"[dry-run] {cmd}")
        else:
            rc = subprocess.call(cmd, shell=True, cwd=root)
            if rc != 0:
                return rc
    return 0


def handle_map(fmt: str, flt: str | None, do_open: bool) -> int:
    reg = load_registry()
    projects = filter_projects(reg, flt)
    groups = {"engine": [], "host": [], "host_core": [], "shared": [], "integration": [], "library": [], "misc": []}
    for name, meta in projects.items():
        groups.get(meta.get("type", "misc"), groups["misc"]).append((name, meta))

    if fmt == "ansi":
        total = 0
        for g, items in groups.items():
            if not items:
                continue
            print(f"[{g}]")
            for name, meta in items:
                total += 1
                deps = ", ".join(meta.get("deps", [])) or "none"
                run = "yes" if meta.get("run") else "no"
                tests = ", ".join(meta.get("tests", [])) or "none"
                print(f"  - {name} ({meta.get('path')}) deps: {deps} tests: {tests} run: {run}")
        leafs = [n for n, m in projects.items() if not m.get("deps")]
        print(f"[ma] projects: {total}; leaf nodes: {len(leafs)}")
        return 0
    if fmt == "mermaid":
        print("graph TD")
        for name, meta in projects.items():
            for dep in meta.get("deps", []):
                print(f"  {dep} --> {name}")
        return 0
    if fmt in ("dot", "svg", "html"):
        dot_lines = ["digraph G {"] + [
            f'  "{dep}" -> "{name}";'
            for name, meta in projects.items()
            for dep in meta.get("deps", [])
        ] + ["}"]
        if fmt == "dot":
            print("\n".join(dot_lines))
            return 0
        if fmt == "svg":
            if shutil.which("dot") is None:
                print("[ma] graphviz dot not found; install graphviz or use --graph dot/mermaid/text.")
                return 1
            proc = subprocess.run(["dot", "-Tsvg"], input="\n".join(dot_lines), text=True, capture_output=True)
            if proc.returncode != 0:
                print(proc.stderr)
                return proc.returncode
            svg_out = proc.stdout
            print(svg_out)
            if do_open and shutil.which("open"):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".svg")
                tmp.write(svg_out.encode("utf-8"))
                tmp.close()
                subprocess.call(["open", tmp.name])
            return 0
        if fmt == "html":
            html_body = "\n".join(dot_lines)
            print(f"<pre>{html_body}</pre>")
            return 0
    for name, meta in projects.items():
        deps = ", ".join(meta.get("deps", [])) or "none"
        print(f"{name}: {deps}")
    return 0


def handle_profile(args, runtime: RuntimeConfig = None) -> int:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root
    profiles = {
        "audio-dev": {"sparse": ["engines/audio_engine", "shared"], "playbook": "pipeline-dev"},
        "host-dev": {"sparse": ["hosts", "shared"], "playbook": "host-dev"},
    }
    action = args.action
    if action == "list":
        for name in sorted(profiles.keys()):
            print(name)
        return 0
    if action == "show":
        prof = profiles.get(args.name)
        if not prof:
            print(f"[ma] profile '{args.name}' not found")
            return 1
        print(json.dumps(prof, indent=2))
        return 0
    if action == "apply":
        prof = profiles.get(args.name)
        if not prof:
            print(f"[ma] profile '{args.name}' not found")
            return 1
        steps = []
        if "sparse" in prof:
            steps.append(f"ma sparse --set {' '.join(prof['sparse'])}")
        if "playbook" in prof:
            steps.append(f"ma playbook {prof['playbook']}")
        print(f"[ma] applying profile {args.name}:")
        for step in steps:
            print(f"- {step}")
            if not args.dry_run:
                subprocess.call(step, shell=True, cwd=root)
        return 0
    return 1


def handle_completion(shell: str, parser_builder) -> int:
    p = parser_builder()
    if shell == "bash":
        print(p.format_usage())
    elif shell == "zsh":
        print("#compdef ma\n_arguments '*: :->cmds'")
    return 0


def _load_idx(progress_path) -> int:
    if progress_path.exists():
        try:
            return json.loads(progress_path.read_text()).get("idx", 0)
        except Exception:
            return 0
    return 0


def _save_idx(progress_path, idx: int, runtime: RuntimeConfig = None) -> None:
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import CACHE_ENABLED, STATE_HOME
        cache_enabled, state_home = CACHE_ENABLED, STATE_HOME
    else:
        cache_enabled, state_home = runtime.cache_enabled, runtime.state_home

    if not cache_enabled:
        return
    try:
        state_home.mkdir(parents=True, exist_ok=True)
        progress_path.write_text(json.dumps({"idx": idx}))
    except Exception:
        print("[ma] warning: could not save tour progress.")


def handle_tour(reset: bool = False, advance: bool = False, runtime: RuntimeConfig = None) -> int:
    """Guided breadcrumb/tour with lightweight progress tracking."""
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import STATE_HOME
        state_home = STATE_HOME
    else:
        state_home = runtime.state_home

    steps = [
        {"title": "Discover projects", "cmd": "ma list", "desc": "See all projects and paths."},
        {"title": "Pick a target", "cmd": "ma select", "desc": "Interactive picker for test/run/deps."},
        {"title": "Check changes", "cmd": "ma affected --base origin/main", "desc": "Run tests for changed projects."},
        {"title": "Watch health", "cmd": "ma dashboard --live", "desc": "Live repo dashboard (Rich)."},
        {"title": "Run gate", "cmd": "ma verify", "desc": "Lint + type + smoke + affected."},
        {"title": "Full sweep", "cmd": "ma test-all --cache", "desc": "Run the full suite with cache hints."},
        {"title": "Task graph", "cmd": "ma tasks-run test-all --cache", "desc": "Nx/Turbo-style task runner demo."},
        {"title": "Git status", "cmd": "ma git-status --branches", "desc": "Check branch/dirty/ahead/behind and recents."},
        {"title": "Branch helper", "cmd": "ma git-branch <project> --desc work", "desc": "Create a scoped feature branch."},
        {"title": "Preflight push", "cmd": "ma github-check --require-clean --require-upstream", "desc": "Pre-push/CI readiness gate."},
        {"title": "Doctor tests", "cmd": "ma doctor --check-tests", "desc": "Ensure test paths are wired."},
    ]
    progress_path = state_home / "tour_progress.json"
    idx = 0 if reset else _load_idx(progress_path)
    idx = max(0, min(idx, len(steps)))

    if advance:
        idx = min(idx + 1, len(steps))
        _save_idx(progress_path, idx, runtime)

    def render(idx_val: int):
        try:
            from rich.table import Table
            from rich.console import Console
            table = Table(title="ma helper tour", show_header=True, header_style="bold cyan", expand=True)
            table.add_column("step")
            table.add_column("status")
            table.add_column("command")
            table.add_column("description")
            for i, step in enumerate(steps):
                status = "✅ done" if i < idx_val else ("▶ next" if i == idx_val else "… pending")
                table.add_row(f"{i+1}", status, step["cmd"], step["desc"])
            Console().print(table)
        except Exception:
            print("ma helper tour:")
            for i, step in enumerate(steps):
                status = "[done]" if i < idx_val else ("[next]" if i == idx_val else "[ ]")
                print(f"{status} {i+1}. {step['cmd']} — {step['desc']}")

    render(idx)
    if idx < len(steps):
        next_step = steps[idx]
        print(f"Next: {next_step['cmd']}  ({next_step['desc']})")
        print("Auto-advance: run the command or use --advance. Reset with: ma tour --reset")
    else:
        print("Tour complete. Reset anytime with: ma tour --reset")

    if reset:
        _save_idx(progress_path, 0, runtime)
    elif advance:
        _save_idx(progress_path, idx, runtime)
    return 0


# --- Tour auto-advance helper (called from CLI dispatcher) ---
def maybe_advance_tour(cmd_name: str, runtime: RuntimeConfig = None) -> None:
    """Auto-advance the tour when a matching command succeeds."""
    # Backward compatibility
    if runtime is None:
        from ma_helper.core.env import CACHE_ENABLED, STATE_HOME
        cache_enabled, state_home = CACHE_ENABLED, STATE_HOME
    else:
        cache_enabled, state_home = runtime.cache_enabled, runtime.state_home

    if not cache_enabled:
        return
    steps = [
        "list",
        "select",
        "affected",
        "dashboard",
        "verify",
        "test-all",
        "tasks-run",
        "git-status",
        "git-branch",
        "github-check",
        "doctor",
    ]
    if cmd_name not in steps:
        return
    progress_path = state_home / "tour_progress.json"
    idx = 0
    try:
        if progress_path.exists():
            idx = json.loads(progress_path.read_text()).get("idx", 0)
    except Exception:
        idx = 0
    # Only advance if we are at or before the matching step.
    target = steps.index(cmd_name)
    if idx <= target:
        idx = target + 1
        try:
            state_home.mkdir(parents=True, exist_ok=True)
            progress_path.write_text(json.dumps({"idx": idx}))
        except Exception:
            pass
