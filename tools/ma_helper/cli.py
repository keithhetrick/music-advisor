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
import concurrent.futures
import importlib.util
import json
import time
import os
import shutil
import subprocess
import sys
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import json as jsonlib

STATE_HOME = Path(os.environ.get("MA_HELPER_HOME", Path.home() / ".ma_helper"))
try:
    STATE_HOME.mkdir(parents=True, exist_ok=True)
except Exception:
    # fallback to tmp if home is not writable
    try:
        STATE_HOME = Path("/tmp/ma_helper")
        STATE_HOME.mkdir(parents=True, exist_ok=True)
    except Exception:
        STATE_HOME = Path.cwd()
LOG_DIR = STATE_HOME / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / "ma.log"
except Exception:
    LOG_DIR = None
    LOG_FILE = None
DRY_RUN = False

ROOT = Path(__file__).resolve().parents[2]
FAVORITES_PATH = STATE_HOME / "config.json"
CACHE_DIR = ROOT / ".ma_cache"
CACHE_FILE = CACHE_DIR / "cache.json"
LAST_RESULTS_FILE = CACHE_DIR / "last_results.json"
ARTIFACT_DIR = CACHE_DIR / "artifacts"
CONFIG = {
    "guard": "normal",  # normal | strict
}

orch_path = ROOT / "tools" / "ma_orchestrator.py"
spec = importlib.util.spec_from_file_location("ma_orchestrator", orch_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load ma_orchestrator.py")
orch = importlib.util.module_from_spec(spec)
sys.modules["ma_orchestrator"] = orch
spec.loader.exec_module(orch)

# Friendly task aliases (mirrors Makefile/Taskfile)
TASKS: Dict[str, str] = {
    "test-all": "python tools/ma_orchestrator.py test-all",
    "test-affected": "python tools/ma_orchestrator.py test-affected --base origin/main",
    "test-audio": "python tools/ma_orchestrator.py test audio_engine",
    "test-lyrics": "python tools/ma_orchestrator.py test lyrics_engine",
    "test-ttc": "python tools/ma_orchestrator.py test ttc_engine",
    "test-reco": "python tools/ma_orchestrator.py test recommendation_engine",
    "test-host": "python tools/ma_orchestrator.py test advisor_host",
    "test-host-core": "python tools/ma_orchestrator.py test advisor_host_core",
    "test-root": "python tools/ma_orchestrator.py test root_integration",
    "run-audio-cli": "python tools/ma_orchestrator.py run audio_engine",
    "run-lyrics-cli": "python tools/ma_orchestrator.py run lyrics_engine",
    "run-ttc-cli": "python tools/ma_orchestrator.py run ttc_engine",
    "run-reco-cli": "python tools/ma_orchestrator.py run recommendation_engine",
    "run-advisor-host": "python tools/ma_orchestrator.py run advisor_host",
}


def cmd_tasks(filter_substr: str | None = None, as_json: bool = False) -> int:
    items = [(name, cmd) for name, cmd in TASKS.items() if not filter_substr or filter_substr in name or filter_substr in cmd]
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


def load_favorites() -> Dict[str, Any]:
    if not FAVORITES_PATH.exists():
        return {"favorites": [], "history": [], "theme": {}, "last_failed": "", "last_base": "", "guard": "normal"}
    try:
        data = json.loads(FAVORITES_PATH.read_text())
        if "guard" not in data:
            data["guard"] = "normal"
        return data
    except Exception:
        return {"favorites": [], "history": [], "theme": {}, "last_failed": "", "last_base": "", "guard": "normal"}


def save_favorites(data: Dict[str, Any]) -> None:
    try:
        FAVORITES_PATH.write_text(json.dumps(data, indent=2))
    except Exception as exc:
        print(f"[ma] warning: could not persist prefs ({exc})", file=sys.stderr)


def guard_level() -> str:
    return load_favorites().get("guard", "normal")


def set_guard_level(level: str) -> None:
    data = load_favorites()
    data["guard"] = level
    save_favorites(data)


def add_history(cmd: str) -> None:
    data = load_favorites()
    hist = data.get("history", [])
    hist.append(cmd)
    data["history"] = hist[-50:]
    save_favorites(data)


def ensure_favorite(name: str, cmd: str) -> None:
    data = load_favorites()
    favs = data.get("favorites", [])
    favs = [f for f in favs if f.get("name") != name]
    favs.append({"name": name, "cmd": cmd})
    data["favorites"] = favs
    save_favorites(data)


def set_last_failed(cmd: str) -> None:
    data = load_favorites()
    data["last_failed"] = cmd
    save_favorites(data)


def set_last_base(base: str) -> None:
    data = load_favorites()
    data["last_base"] = base
    save_favorites(data)


def load_cache() -> Dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}


def save_cache(cache: Dict[str, Any]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception as exc:
        print(f"[ma] warning: could not persist cache ({exc})", file=sys.stderr)


def write_artifact(project, target: str, info: Dict[str, Any]) -> None:
    try:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        meta = {
            "project": project.name,
            "target": target,
            "hash": info.get("hash"),
            "ts": time.time(),
        }
        path = ARTIFACT_DIR / f"{project.name}_{target}.json"
        path.write_text(json.dumps(meta, indent=2))
    except Exception:
        pass


def _hash_dir(paths: List[Path]) -> str:
    """Lightweight hash based on file path + size + mtime to stay fast."""
    h = hashlib.sha256()
    for base in paths:
        if not base.exists():
            continue
        for root, dirs, files in os.walk(base):
            # skip noisy dirs
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".venv", ".mypy_cache", ".pytest_cache", ".ma_cache"}]
            for fname in files:
                p = Path(root) / fname
                try:
                    stat = p.stat()
                except FileNotFoundError:
                    continue
                rel = p.relative_to(ROOT).as_posix()
                h.update(rel.encode())
                h.update(str(stat.st_mtime_ns).encode())
                h.update(str(stat.st_size).encode())
    return h.hexdigest()


def hash_project(project) -> str:
    paths = [project.path] + [ROOT / t for t in project.tests]
    return _hash_dir(paths)


def should_skip_cached(project, target: str, cache_mode: str) -> Tuple[bool, Dict[str, Any]]:
    if cache_mode == "off":
        return False, {}
    cache = load_cache()
    entry = cache.get(project.name, {})
    cache_key = f"{target}_hash"
    current = hash_project(project)
    if entry.get(cache_key) == current:
        return True, {"project": project.name, "rc": 0, "duration": 0.0, "cached": True}
    return False, {"project": project.name, "rc": 0, "duration": 0.0, "cached": False, "hash": current}


def update_cache(project, target: str, info: Dict[str, Any], cache_mode: str) -> None:
    if cache_mode == "restore-only":
        return
    cache = load_cache()
    entry = cache.get(project.name, {})
    cache_key = f"{target}_hash"
    if "hash" in info:
        entry[cache_key] = info["hash"]
    entry["updated_at"] = time.time()
    cache[project.name] = entry
    save_cache(cache)



def list_favorites(as_json: bool = False) -> int:
    data = load_favorites()
    favs = data.get("favorites", [])
    hist = data.get("history", [])
    theme = data.get("theme", {})
    last_base = data.get("last_base", "")
    last_failed = data.get("last_failed", "")
    if as_json:
        print(json.dumps({"favorites": favs, "history": hist, "theme": theme, "last_base": last_base, "last_failed": last_failed}, indent=2))
        return 0
    print("Favorites:")
    for fav in favs:
        print(f"- {fav.get('name')}: {fav.get('cmd')}")
    print("\nRecent history:")
    for h in hist[-10:]:
        print(f"- {h}")
    if theme:
        print("\nTheme:")
        for k, v in theme.items():
            print(f"- {k}: {v}")
    if last_base:
        print(f"\nLast base: {last_base}")
    if last_failed:
        print(f"Last failed command: {last_failed}")
    return 0


def cmd_select(projects) -> int:
    names = list(projects.keys())
    theme = load_favorites().get("theme", {})
    prompt_color = theme.get("prompt_color", "ansicyan")
    while True:
        project = None
        # Try prompt_toolkit for fuzzy select
        try:
            from prompt_toolkit import prompt
            from prompt_toolkit.completion import FuzzyWordCompleter
            from prompt_toolkit.styles import Style

            style = Style.from_dict({
                "prompt": prompt_color,
                "": "",
            })
            completer = FuzzyWordCompleter(names, sentence=True)
            choice = prompt([("class:prompt", "Project (fuzzy, blank to exit): ")], completer=completer, style=style).strip()
            if not choice:
                print("Done.")
                return 0
            if choice and choice in projects:
                project = projects[choice]
        except Exception:
            pass

        if project is None:
            print("Select a project (blank to exit):")
            for idx, name in enumerate(names, start=1):
                p = projects[name]
                print(f"{idx}. {name:24} [{p.type}] - {p.path.relative_to(orch.ROOT)}")
            raw = input("Enter number (or blank to cancel): ").strip()
            if not raw:
                print("Done.")
                return 0
            try:
                idx = int(raw)
                project = projects[names[idx - 1]]
            except Exception:
                print("Invalid selection.")
                continue

        actions = {
            "test": "Run tests",
            "run": "Run target",
            "deps": "Show deps",
            "affected": "Run affected tests",
            "watch": "Watch and rerun tests",
            "back": "Go back to project selection",
        }
        action = None
        try:
            from prompt_toolkit import prompt
            from prompt_toolkit.completion import FuzzyWordCompleter
            from prompt_toolkit.styles import Style

            style = Style.from_dict({"prompt": prompt_color})
            completer = FuzzyWordCompleter(list(actions.keys()), sentence=True)
            choice = prompt([("class:prompt", "Action (test/run/deps/affected/watch): ")], completer=completer, style=style).strip().lower()
            if choice in actions:
                action = choice
        except Exception:
            pass
        if action is None:
            action = input("Action: (t)est, (r)un (if available), (d)eps, (a)ffected, (w)atch? ").strip().lower()
            if action.startswith("t"):
                action = "test"
            elif action.startswith("r"):
                action = "run"
            elif action.startswith("d"):
                action = "deps"
            elif action.startswith("a"):
                action = "affected"
            elif action.startswith("w"):
                action = "watch"
            elif action == "" or action.startswith("b"):
                action = "back"
            else:
                action = None

        if action == "back":
            continue
        if action == "test":
            add_history(f"python tools/ma_orchestrator.py test {project.name}")
            orch.run_tests_for_project(project)
        elif action == "run":
            add_history(f"python tools/ma_orchestrator.py run {project.name}")
            orch.run_project_target(project)
        elif action == "deps":
            orch.print_deps(projects)
        elif action == "affected":
            base = input("Base ref for affected (default origin/main): ").strip() or "origin/main"
            add_history(f"python tools/ma_orchestrator.py test-affected --base {base}")
            orch.run_affected_tests(projects, base)
        elif action == "watch":
            base_cmd = f"python3 tools/ma_orchestrator.py test {project.name}"
            cmd_watch(project.name, base_cmd)
        else:
            print("Unknown action.")
        # loop again to keep the menu open


def cmd_watch(project_name: str, base_cmd: str) -> int:
    """Watch loop using entr if present, otherwise watchfiles fallback."""
    projects = orch.load_projects()
    if project_name not in projects:
        print(f"[ma] unknown project '{project_name}'.", file=sys.stderr)
        return 1
    project = projects[project_name]
    if not project.path.exists():
        print(f"[ma] project path does not exist: {project.path}", file=sys.stderr)
        return 1
    if guard_level() == "strict":
        if not require_confirm(f"Start watch on {project_name}?"):
            print("[ma] aborted (strict guard).")
            return 1
    # capture optional hooks
    on_success = getattr(cmd_watch, "on_success", None)
    on_fail = getattr(cmd_watch, "on_fail", None)
    preset = getattr(cmd_watch, "preset", None)
    if preset == "test":
        base_cmd = f"python3 tools/ma_orchestrator.py test {project_name}"
    if preset == "lint":
        base_cmd = "./infra/scripts/with_repo_env.sh -m ruff check hosts/advisor_host engines/recommendation_engine/recommendation_engine"
    rerun_failed = getattr(cmd_watch, "rerun_last_failed", False)
    if rerun_failed:
        data = load_favorites()
        last_failed = data.get("last_failed")
        if last_failed:
            print(f"[ma] rerunning last failed command before watch: {last_failed}")
            _run_cmd(last_failed, cwd=orch.ROOT)
    hotkeys = getattr(cmd_watch, "hotkeys", False)
    use_hotkeys = hotkeys
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
        import asyncio
    except Exception:
        print("[ma] install `entr` or `watchfiles` to use watch (pip install watchfiles).", file=sys.stderr)
        return 1
    async def _loop():
        print(f"[ma] watching {project.path} with watchfiles -> {base_cmd}")
        if use_hotkeys:
            print("[ma] hotkeys: r=rerun, f=rerun last failed (if any), q=quit")
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


def cmd_doctor(require_optional: bool = False) -> int:
    ok = True
    def note(msg: str):
        print(f"[ok] {msg}")
    def warn(msg: str):
        nonlocal ok
        ok = False if require_optional else ok
        print(f"[warn] {msg}")
    if (ROOT / ".venv").exists():
        note(".venv present")
    else:
        warn("No .venv found; run make bootstrap-locked")
    if shutil.which("git"):
        note("git present")
    else:
        warn("git not found on PATH")
    if shutil.which("entr") or _has_watchfiles():
        note("watch dependency present (entr or watchfiles)")
    else:
        warn("No watch dependency; install entr or pip install watchfiles")
    if shutil.which("dot"):
        note("graphviz (dot) present for --graph svg")
    else:
        warn("graphviz dot not found (optional)")
    # optional UX deps
    try:
        import importlib.util
        if importlib.util.find_spec("prompt_toolkit"):
            note("prompt_toolkit present (fuzzy/styled prompts)")
        else:
            warn("prompt_toolkit not found (optional for fuzzy/styled prompts)")
        if importlib.util.find_spec("rich"):
            note("rich present (styled tables/JSON)")
        else:
            warn("rich not found (optional for styled output)")
    except Exception:
        pass
    manifest = ROOT / "infra" / "scripts" / "data_manifest.json"
    if manifest.exists():
        note("data_manifest.json present")
    else:
        warn("infra/scripts/data_manifest.json missing")
    return 0 if ok else 1


def cmd_guard(args) -> int:
    if args.set:
        if args.set not in ("normal", "strict"):
            print("[ma] guard must be normal|strict", file=sys.stderr)
            return 1
        set_guard_level(args.set)
        print(f"[ma] guard set to {args.set}")
        return 0
    print(f"[ma] guard: {guard_level()}")
    return 0


def cmd_check() -> int:
    """Quick sanity check: git dirty, venv, optional tools present."""
    ok = True
    def warn(msg: str):
        nonlocal ok
        ok = False
        print(f"[warn] {msg}")
    if not (ROOT / ".venv").exists():
        warn("No .venv found; run make bootstrap-locked")
    if not enforce_permissions(ROOT):
        warn("Cannot write cache/log/prefs; check permissions.")
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            warn("Git working tree is dirty (unstaged/uncommitted changes).")
    except Exception:
        warn("Git status check failed")
    if shutil.which("rich") is None:
        warn("rich not installed (for better UI)")
    if shutil.which("entr") is None and _has_watchfiles() is False:
        warn("No watch backend (entr/watchfiles) installed")
    if guard_level() == "strict":
        print("[ok] guard strict (confirmations enabled)")
    if ok:
        print("[ma] check ok")
        return 0
    return 1


def cmd_github_check(args) -> int:
    ok = True
    def fail(msg: str):
        nonlocal ok
        ok = False
        print(f"[fail] {msg}")
    # ensure git available
    if shutil.which("git") is None:
        fail("git not found on PATH; cannot perform github-check.")
        return 1
    # ensure repo root is a git repo
    if not (ROOT / ".git").exists():
        fail("No .git directory at repo root; github-check expects a git repo.")
        return 1
    # clean tree
    if args.require_clean or os.environ.get("MA_REQUIRE_CLEAN") == "1" or args.require_clean_env:
        try:
            res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
            if res.stdout.strip():
                fail("Git working tree is dirty; commit/stash before pushing.")
        except Exception:
            fail("Unable to check git status (ensure repo initialized).")
    # branch check
    if args.require_branch:
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
            branch = res.stdout.strip()
            if branch != args.require_branch:
                fail(f"On branch '{branch}' but expected '{args.require_branch}'.")
        except Exception:
            fail("Unable to read current branch (maybe detached HEAD?).")
    if args.require_upstream:
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=ROOT, capture_output=True, text=True, check=True)
            upstream = res.stdout.strip()
            print(f"[ma] upstream: {upstream}")
        except Exception:
            fail("No upstream tracking branch set; git rev-parse @{u} failed.")
    # ahead/behind info (informational)
    try:
        base_ref = args.base if getattr(args, "base", None) else "origin/main"
        res = subprocess.run(["git", "rev-list", "--left-right", "--count", f"{base_ref}...HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        ahead, behind = res.stdout.strip().split()
        print(f"[ma] ahead/behind vs {base_ref}: +{ahead} / -{behind}")
    except Exception:
        print("[ma] warning: unable to compute ahead/behind.", file=sys.stderr)
    if args.require_optional or os.environ.get("MA_REQUIRE_OPTIONAL") == "1":
        rc = cmd_doctor(require_optional=True)
        if rc != 0:
            fail("Optional dependencies check failed (rich/watchfiles/entr/graphviz).")
    # preflight
    if args.preflight and cmd_preflight() != 0:
        fail("Preflight failed (missing test/run paths).")
    # verify
    if args.verify and cmd_verify(argparse.Namespace(ignore_failures=False)) != 0:
        fail("Verify failed.")
    # ci-plan dry-run
    if args.ci_plan:
        base = args.base
        try:
            res = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            fail(f"git diff {base}...HEAD failed.")
        else:
            print(f"[ma] ci-plan dry-run vs {base}:")
            main(["ci-plan", "--base", base, "--targets", "test", "--matrix"])
    if ok:
        print("[ma] github-check ok")
        return 0
    return 1


def cmd_hook(args) -> int:
    if args.name != "pre-push":
        print("[ma] only pre-push hook helper is provided.", file=sys.stderr)
        return 1
    hook_path = ROOT / ".git" / "hooks" / "pre-push"
    script = f"""#!/usr/bin/env bash
set -euo pipefail
python -m ma_helper github-check --require-clean --preflight --ci-plan --base origin/main
"""
    if args.install:
        if guard_level() == "strict" or os.environ.get("MA_REQUIRE_CONFIRM") == "1":
            if not require_confirm(f"Install/overwrite git hook at {hook_path}?"):
                print("[ma] aborted hook install.")
                return 1
        hook_path.write_text(script)
        hook_path.chmod(0o755)
        print(f"[ma] pre-push hook installed at {hook_path}")
        return 0
    print(script.strip())
    return 0


def cmd_precommit(args) -> int:
    if args.action == "print":
        script = """#!/usr/bin/env bash
set -euo pipefail
python -m ma_helper preflight
python -m ma_helper lint
python -m ma_helper typecheck
"""
        print(script.strip())
        return 0
    if args.action == "install":
        hook_path = ROOT / ".git" / "hooks" / "pre-commit"
        script = """#!/usr/bin/env bash
set -euo pipefail
python -m ma_helper preflight
python -m ma_helper lint
python -m ma_helper typecheck
"""
        if guard_level() == "strict" or os.environ.get("MA_REQUIRE_CONFIRM") == "1":
            if not require_confirm(f"Install/overwrite git hook at {hook_path}?"):
                print("[ma] aborted hook install.")
                return 1
        hook_path.write_text(script)
        hook_path.chmod(0o755)
        print(f"[ma] pre-commit hook installed at {hook_path}")
        return 0
    return 1


def cmd_chat_dev(args) -> int:
    chat_cmd = f"CHAT_ENDPOINT={args.endpoint} python tools/chat_cli.py"
    tail_cmd = f"tail -f {args.log_file}"
    helper_cmd = "python -m ma_helper shell"
    if shutil.which("tmux"):
        session = "chatdev"
        layout = f"tmux new-session -d -s {session} '{chat_cmd}' \\; split-window -h '{tail_cmd}' \\; split-window -v '{helper_cmd}' \\; select-layout even-horizontal \\; attach-session -t {session}"
        print(f"[ma] launching tmux session '{session}' with chat/tail/shell panes")
        rc = subprocess.call(["bash", "-lc", layout], cwd=orch.ROOT)
        if rc != 0:
            print("[ma] tmux launch failed; falling back to manual commands.")
        else:
            return rc
    else:
        print("[ma] tmux not found; run these in three terminals:")
        print(f"1) {chat_cmd}")
        print(f"2) {tail_cmd}")
        print(f"3) {helper_cmd}")
        return 0
    # fallback if tmux failed
    print("1) " + chat_cmd)
    print("2) " + tail_cmd)
    print("3) " + helper_cmd)
    return 0


def cmd_preflight() -> int:
    """Lightweight preflight: check test paths and run targets for existence."""
    projects = orch.load_projects()
    missing_tests = []
    missing_run = []
    for proj in projects.values():
        for t in proj.tests:
            pth = ROOT / t
            if not pth.exists():
                missing_tests.append((proj.name, t))
        if proj.run:
            # only check first element if it looks like a path
            first = proj.run[0]
            if first.startswith("./"):
                rp = ROOT / first
                if not rp.exists():
                    missing_run.append((proj.name, first))
    ok = True
    if missing_tests:
        ok = False
        print("[ma] missing test paths:")
        for name, t in missing_tests:
            print(f" - {name}: {t}")
    if missing_run:
        ok = False
        print("[ma] missing run targets (first element not found):")
        for name, r in missing_run:
            print(f" - {name}: {r}")
    if ok:
        print("[ma] preflight ok (tests/run entries present)")
        return 0
    return 1


def _has_watchfiles() -> bool:
    try:
        import importlib
        return importlib.util.find_spec("watchfiles") is not None
    except Exception:
        return False


def cmd_sparse(args) -> int:
    if args.list:
        return _run_cmd("git sparse-checkout list", cwd=orch.ROOT)
    if args.reset:
        if not require_confirm("Disable sparse-checkout?"):
            print("[ma] aborting (strict guard).")
            return 1
        return _run_cmd("git sparse-checkout disable", cwd=orch.ROOT)
    if args.set:
        paths = args.set
        print(f"[ma] enabling cone mode and setting paths: {paths}")
        rc = _run_cmd("git sparse-checkout init --cone", cwd=orch.ROOT)
        if rc != 0:
            return rc
        return _run_cmd("git sparse-checkout set " + " ".join(paths), cwd=orch.ROOT)
    print("Usage: sparse --list | --reset | --set <paths...>")
    return 1


def cmd_scaffold(args) -> int:
    base = Path(args.path) if args.path else ROOT / "tools" / "scaffolds" / args.name
    base.mkdir(parents=True, exist_ok=True)
    (base / "README.md").write_text(f"# {args.name}\n\nScaffolded {args.type} project stub.\n")
    (base / "pyproject.toml").write_text(f"""[project]
name = "{args.name}"
version = "0.0.0"
description = "Scaffolded {args.type} project"
requires-python = ">=3.10"
""")
    (base / "tests").mkdir(exist_ok=True)
    (base / "tests" / "test_import_smoke.py").write_text(
        "def test_import_smoke():\n    assert True\n"
    )
    print(f"[ma] Scaffold created at {base} (not added to registry/project_map).")
    if args.write_registry:
        if guard_level() == "strict" and not require_confirm("Update project_map.json with scaffold entry?"):
            print("[ma] registry update aborted (strict guard).")
            return 0
        reg = load_registry()
        rel_path = str(base.relative_to(ROOT))
        reg[args.name] = {
            "path": rel_path,
            "tests": [f"{rel_path}/tests"],
            "description": f"Scaffolded {args.type} project",
            "type": args.type,
            "deps": [],
        }
        (ROOT / "project_map.json").write_text(json.dumps(dict(sorted(reg.items())), indent=2))
        print("[ma] registry updated with scaffold entry")
    return 0


SMOKE_CMDS = {
    # use the repo's smoke wrappers (they set PYTHONPATH internally)
    "pipeline": "./infra/scripts/quick_check.sh",
    "full": "./infra/scripts/e2e_app_smoke.sh",
}


def cmd_smoke(target: str) -> int:
    if target == "menu":
        print("Smokes:")
        for key, val in SMOKE_CMDS.items():
            print(f"- {key}: {val}")
        return 0
    cmd = SMOKE_CMDS.get(target)
    if not cmd:
        print(f"[ma] unknown smoke target {target}", file=sys.stderr)
        return 1
    print(f"[ma] running smoke '{target}': {cmd}")
    return _run_cmd(cmd, cwd=orch.ROOT)


def cmd_lint() -> int:
    cmd = "./infra/scripts/with_repo_env.sh -m ruff check hosts/advisor_host engines/recommendation_engine/recommendation_engine"
    return _run_cmd(cmd, cwd=orch.ROOT)


def cmd_typecheck() -> int:
    cmd = "./infra/scripts/with_repo_env.sh -m mypy --config-file hosts/advisor_host/pyproject.toml hosts/advisor_host"
    return _run_cmd(cmd, cwd=orch.ROOT)


def cmd_format() -> int:
    cmd = "./infra/scripts/with_repo_env.sh -m ruff format hosts/advisor_host engines/recommendation_engine/recommendation_engine"
    return _run_cmd(cmd, cwd=orch.ROOT)


def cmd_verify(args) -> int:
    steps = [
        ("lint", cmd_lint),
        ("typecheck", cmd_typecheck),
        ("smoke pipeline", lambda: cmd_smoke("pipeline")),
        ("affected", lambda: main(["affected", "--no-diff"])),
    ]
    for label, fn in steps:
        print(f"[ma] verify -> {label}")
        rc = fn()
        if rc != 0 and not args.ignore_failures:
            return rc
    return 0


def cmd_ci_env() -> int:
    envs = {
        "AWS_PROFILE": "Set if using AWS CLI creds",
        "AWS_REGION": "Region for data fetch",
        "MA_DATA_ROOT": "Override data root (defaults inside repo)",
        "PYTHONPATH": "Repo root if needed for tooling",
        "LOG_JSON": "Set to 1 for JSON logs (if supported by scripts)",
    }
    print(json.dumps(envs, indent=2))
    return 0


def cmd_rerun_last() -> int:
    data = load_favorites()
    hist = data.get("history", [])
    if not hist:
        print("[ma] no history yet", file=sys.stderr)
        return 1
    last = hist[-1]
    return _run_cmd(last, cwd=orch.ROOT)


def cmd_history(limit: int) -> int:
    data = load_favorites()
    hist = data.get("history", [])
    for entry in hist[-limit:]:
        print(f"- {entry}")
    return 0


def _log_event(entry: Dict[str, Any]) -> None:
    cfg = load_favorites()
    if cfg.get("logging_disabled"):
        return
    if LOG_FILE is None:
        return
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _run_cmd(cmd: str, *, cwd: Path | None = None, dry_run: bool = False) -> int:
    effective_dry = dry_run or DRY_RUN
    print(f"[ma] {cmd}" + (" [dry-run]" if effective_dry else ""))
    if effective_dry:
        return 0
    start = None
    try:
        import time
        start = time.time()
    except Exception:
        pass
    rc = subprocess.call(cmd, shell=True, cwd=cwd or orch.ROOT)
    if start is not None:
        import time
        _log_event({"cmd": cmd, "rc": rc, "duration_sec": round(time.time() - start, 3)})
    if rc != 0:
        set_last_failed(cmd)
    return rc


def require_confirm(prompt: str) -> bool:
    # also honor env override
    if guard_level() != "strict" and os.environ.get("MA_REQUIRE_CONFIRM") != "1":
        return True
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
        return ans in ("y", "yes")
    except Exception:
        return False


def enforce_permissions(path: Path) -> bool:
    """Warn (but do not abort) if key helper files are not writable."""
    targets = [FAVORITES_PATH, CACHE_DIR, CACHE_FILE, LAST_RESULTS_FILE, LOG_DIR or STATE_HOME]
    ok = True
    for t in targets:
        parent = t if t.suffix else t
        try:
            parent.parent.mkdir(parents=True, exist_ok=True)
            test = parent if parent.suffix else parent / ".touch"
            test.touch(exist_ok=True)
        except Exception:
            ok = False
            print(f"[ma] warning: cannot write to {t}; some features (cache/logs/prefs) may be disabled.")
    return ok


def enforce_clean_tree() -> bool:
    """If MA_REQUIRE_CLEAN=1, ensure git working tree is clean."""
    if os.environ.get("MA_REQUIRE_CLEAN") != "1":
        return True
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        print("[ma] warning: MA_REQUIRE_CLEAN=1 but git/.git not available; skipping clean check.", file=sys.stderr)
        return True
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
        if res.stdout.strip():
            print("[ma] git working tree is dirty (MA_REQUIRE_CLEAN=1). Commit or stash, or unset MA_REQUIRE_CLEAN.", file=sys.stderr)
            return False
    except Exception:
        print("[ma] warning: unable to check git status; proceeding.", file=sys.stderr)
    return True


def _git_summary() -> Dict[str, str]:
    summary = {"branch": "unknown", "dirty": "?"}
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        return summary
    try:
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        summary["branch"] = res.stdout.strip()
    except Exception:
        pass
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
        summary["dirty"] = "dirty" if res.stdout.strip() else "clean"
    except Exception:
        pass
    return summary


def print_ma_banner():
    """Print a short banner to signal the Music Advisor helper context."""
    try:
        from ma_helper.ui_world import print_banner
        print_banner(ROOT, guard_level())
    except Exception:
        summary = _git_summary()
        guard = guard_level()
        bar = f"branch: {summary.get('branch','?')}  |  tree: {summary.get('dirty','?')}  |  guard: {guard}"
        banner_lines = [
            "╔════════════════════════════════════════╗",
            "║ Music Advisor Helper (monorepo tools)  ║",
            "║ ma quickstart  → top commands          ║",
            "║ ma welcome    → overview               ║",
            "║ ma palette    → common ops             ║",
            "║ ma list       → projects               ║",
            "╠════════════════════════════════════════╣",
            f"║ {bar.ljust(38)[:38]} ║",
            "╚════════════════════════════════════════╝",
        ]
        print("\n".join(banner_lines))


def cmd_welcome() -> int:
    try:
        from ma_helper.ui_world import print_banner
        print_banner(ROOT, guard_level())
        from ma_helper.ui_world import hint
    except Exception:
        hint = lambda msg: None  # type: ignore
        print_ma_banner()
    intro = (
        "You are in the Music Advisor helper: monorepo-friendly commands with project awareness, "
        "affected logic, interactive picker, smokes, and utilities. Use quickstart/palette to explore."
    )
    cmds = [
        ("list", "List projects/paths"),
        ("select", "Interactive project/action picker (fuzzy if prompt_toolkit)"),
        ("tasks", "Show common task aliases"),
        ("test-all", "Run all tests [--parallel N]"),
        ("affected", "Run tests for changed projects [--base ref] [--parallel N]"),
        ("deps", "Show dependency graph [--graph mermaid|dot|svg|text]"),
        ("watch", "Watch a project and rerun on change [--cmd ...]"),
        ("ci-plan", "Print affected JSON for CI planning"),
        ("doctor", "Check env/tools (venv/git/watch/graphviz/manifest)"),
        ("sparse", "Manage git sparse-checkout"),
        ("smoke", "Run pipeline/full smokes"),
        ("lint/typecheck/format", "Repo lint/type/format wrappers"),
        ("favorites", "Save/run command favorites; view history"),
        ("rerun-last", "Re-run the last recorded command"),
    ]
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("command", style="cyan")
        table.add_column("description")
        for cmd, desc in cmds:
            table.add_row(cmd, desc)
        console.print(Panel.fit(intro, title="Welcome", border_style="cyan"))
        console.print(table)
        console.print("[dim]Tip: install prompt_toolkit and rich for best UX; watchfiles for watch fallback; entr/graphviz are optional.[/]")
        return 0
    except Exception:
        print(intro)
        print("Commands:")
        for cmd, desc in cmds:
            print(f"- {cmd}: {desc}")
        print("Tip: install prompt_toolkit and rich for best UX; watchfiles for watch fallback; entr/graphviz are optional.")
        return 0
    try:
        hint("Next: ma quickstart | ma palette | ma list")
    except Exception:
        pass


def cmd_help() -> int:
    """Slightly richer help/command palette."""
    try:
        from ma_helper.ui_world import heading, hint
        heading("Music Advisor helper: command palette")
    except Exception:
        hint = lambda msg: None  # type: ignore
    sections = {
        "Core": [
            ("list", "List projects/paths"),
            ("tasks", "Common aliases"),
            ("select", "Interactive picker (fuzzy if prompt_toolkit)"),
            ("welcome", "Quick overview"),
            ("tour", "Guided tour with prompts"),
            ("dashboard", "Quick overview: counts + last results"),
            ("shell", "Stay in a REPL-style helper shell"),
        ],
        "Execution": [
            ("test <proj>", "Run tests for a project"),
            ("test-all", "Run all tests [--parallel N] [--cache]"),
            ("affected", "Run only changed projects [--base ref|--base-from last|--since X|--merge-base] [--parallel N] [--cache] [--retries]"),
            ("run <proj>", "Run project target if configured"),
            ("run <proj>:target", "Run a specific target (test/run)"),
            ("watch <proj>", "Watch and rerun on change [--preset test|lint] [--rerun-last-failed]"),
        ],
        "Insights": [
            ("deps", "Dependency graph (text/mermaid/dot/svg/ansi)"),
            ("map", "Topology grouped by type; HTML/mermaid/svg"),
            ("info <proj>", "Registry info + dependents + doc links"),
            ("registry validate", "Check project_map.json"),
            ("logs", "Tail helper logs"),
            ("dashboard --json|--html", "Export dashboard"),
        ],
        "CI/Workflow": [
            ("ci-plan", "Affected JSON/matrix [--gha] [--base-from last]"),
            ("playbook", "Preset flows (pipeline-dev/host-dev/sidecar-dev)"),
            ("sparse", "Git sparse helpers"),
            ("smoke", "Smokes: pipeline/full/menu"),
            ("profile apply <name>", "Apply preset actions (sparse/playbook)"),
            ("verify", "Lint+type+smoke+affected in order"),
            ("ci-env", "Print env vars hints for CI jobs"),
        ],
        "Quality": [
            ("lint/typecheck/format", "Repo lint/type/format wrappers"),
            ("doctor", "Env/tooling checks"),
            ("guard --set strict", "Require confirmations for risky actions"),
        ],
        "Productivity": [
            ("favorites ...", "Save/run/list favorites"),
            ("rerun-last", "Run last command in history"),
            ("history", "Show recorded history"),
        ],
    }
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        console = Console()
        for title, rows in sections.items():
            table = Table(show_header=False, box=None)
            table.add_column("cmd", style="cyan")
            table.add_column("desc")
            for cmd, desc in rows:
                table.add_row(cmd, desc)
            console.print(Panel(table, title=title, border_style="magenta"))
        console.print("[dim]Tip: set alias `ma=\"python -m ma_helper\"` for shorter commands. Global --dry-run goes before the command (e.g. `python -m ma_helper --dry-run test-all`).[/]")
    except Exception:
        pass
    for title, rows in sections.items():
        print(f"{title}:")
        for cmd, desc in rows:
            print(f"- {cmd}: {desc}")
    print("Tip: set alias `ma=\"python -m ma_helper\"` and use --dry-run before the command.")
    try:
        hint("Next: ma quickstart | ma palette | ma list")
    except Exception:
        pass
    return 0


def cmd_quickstart() -> int:
    try:
        from ma_helper.ui_world import print_banner
        print_banner(ROOT, guard_level())
        from ma_helper.ui_world import hint
    except Exception:
        hint = lambda msg: None  # type: ignore
        print_ma_banner()
    tips = [
        "ma list                    # list projects",
        "ma test <proj> --cache local",
        "ma affected --base origin/main --require-preflight",
        "ma ci-plan --base origin/main --matrix",
        "ma github-check --require-clean --preflight --ci-plan",
        "ma dashboard --live        # if rich is installed",
    ]
    print("Quickstart commands:")
    for t in tips:
        print(f"- {t}")
    print("More: ma help / ma palette / docs/tools/helper_cli.md")
    hint("Next: ma list | ma affected --base origin/main | ma dashboard --json")
    return 0


def cmd_palette() -> int:
    try:
        from ma_helper.ui_world import print_banner
        print_banner(ROOT, guard_level())
        from ma_helper.ui_world import hint
    except Exception:
        hint = lambda msg: None  # type: ignore
        print_ma_banner()
    print("You are in the Music Advisor helper. Common commands:")
    palette = {
        "list": "list projects",
        "tasks": "common aliases",
        "test": "test <project> [--cache off|local|restore-only]",
        "test-all": "test-all [--parallel N] [--cache ...] [--require-preflight]",
        "affected": "affected --base origin/main [--require-preflight]",
        "run": "run <project>[:run|test]",
        "watch": "watch <project> [--hotkeys] [--require-preflight]",
        "verify": "verify [--require-preflight]",
        "preflight": "check registry paths",
        "dashboard": "dashboard --live|--json|--html",
        "tui": "tui --interval 1 --duration 60",
        "guard": "guard --set strict",
        "doctor": "doctor [--require-optional]",
        "ci-plan": "ci-plan --base origin/main --targets test run",
    }
    try:
        from rich.table import Table
        from rich.console import Console
        console = Console()
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("cmd", style="cyan")
        table.add_column("usage")
        for k, v in palette.items():
            table.add_row(k, v)
        console.print(table)
    except Exception:
        for k, v in palette.items():
            print(f"- {k}: {v}")
    hint("Next: ma list | ma select | ma quickstart")
    return 0


def _post_list_hint():
    try:
        from ma_helper.ui_world import hint
        hint("Tip: ma select for an interactive picker; ma affected --base origin/main to run just changed projects.")
    except Exception:
        pass


def _post_affected_hint():
    try:
        from ma_helper.ui_world import hint
        hint("Tip: ma ci-plan --base origin/main --matrix | ma verify | ma dashboard --json")
    except Exception:
        pass


def load_registry() -> Dict[str, Any]:
    try:
        return json.loads((ROOT / "project_map.json").read_text())
    except Exception:
        return {}


def _filter_projects(projects: Dict[str, Any], substr: str | None) -> Dict[str, Any]:
    if not substr:
        return projects
    return {k: v for k, v in projects.items() if substr in k or substr in v.get("path", "")}


def cmd_map(fmt: str, flt: str | None, do_open: bool) -> int:
    reg = load_registry()
    projects = _filter_projects(reg, flt)
    groups = {"engine": [], "host": [], "host_core": [], "shared": [], "integration": [], "misc": []}
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
                print("[ma] graphviz dot not found; use --graph dot/mermaid/ansi/html.", file=sys.stderr)
                return 1
            proc = subprocess.run(["dot", "-Tsvg"], input="\n".join(dot_lines), text=True, capture_output=True)
            if proc.returncode != 0:
                print(proc.stderr, file=sys.stderr)
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
            mermaid = "graph TD\n" + "\n".join([f"  {dep} --> {name}" for name, meta in projects.items() for dep in meta.get("deps", [])])
            stats = f"Projects: {len(projects)}"
            html = f"""<!doctype html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <script>mermaid.initialize({{startOnLoad:true}});</script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 16px; }}
    .group {{ margin-bottom: 12px; }}
  </style>
</head>
<body>
<h2>Music Advisor Topology</h2>
<p>{stats}</p>
<div class="mermaid">
{mermaid}
</div>
<h3>Groups</h3>
<div class="groups">
"""
            for g, items in groups.items():
                if not items:
                    continue
                html += f"<div class='group'><strong>{g}</strong><ul>"
                for name, meta in items:
                    deps = ", ".join(meta.get("deps", [])) or "none"
                    run = "yes" if meta.get("run") else "no"
                    tests = ", ".join(meta.get("tests", [])) or "none"
                    desc = meta.get("description", "")
                    html += f"<li>{name} ({meta.get('path')}) deps: {deps}; tests: {tests}; run: {run}; {desc}</li>"
                html += "</ul></div>"
            html += "</div></body></html>"
            print(html)
            if do_open and shutil.which("open"):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
                tmp.write(html.encode("utf-8"))
                tmp.close()
                subprocess.call(["open", tmp.name])
            return 0
    print("[ma] unknown map format", file=sys.stderr)
    return 1


def _dashboard_payload() -> Dict[str, Any]:
    reg = load_registry()
    type_counts: Dict[str, int] = {}
    for _, meta in reg.items():
        t = meta.get("type", "misc")
        type_counts[t] = type_counts.get(t, 0) + 1
    last_base = load_favorites().get("last_base", "")
    git_info = {}
    if shutil.which("git"):
        try:
            res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
            dirty_files = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
            git_info["dirty_count"] = len(dirty_files)
            git_info["dirty_files"] = dirty_files[:10]
        except Exception:
            git_info["dirty_count"] = -1
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
            git_info["branch"] = res.stdout.strip()
        except Exception:
            git_info["branch"] = "unknown"
        try:
            res = subprocess.run(["git", "rev-list", "--left-right", "--count", "origin/main...HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
            ahead, behind = res.stdout.strip().split()
            git_info["ahead"] = ahead
            git_info["behind"] = behind
        except Exception:
            git_info["ahead"] = git_info["behind"] = "?"
    last = {}
    if LAST_RESULTS_FILE.exists():
        try:
            last = json.loads(LAST_RESULTS_FILE.read_text())
        except Exception:
            last = {}
    slowest = []
    fail_summary = []
    cache_hits = 0
    total = 0
    if last:
        results = last.get("results", [])
        slowest = sorted(results, key=lambda r: r.get("duration", 0), reverse=True)[:5]
        fail_summary = [r for r in results if r.get("rc") != 0]
        cache_hits = sum(1 for r in results if r.get("cached"))
        total = len(results)
    return {
        "types": type_counts,
        "last": last,
        "slowest": slowest,
        "failures": fail_summary,
        "cache_hit_rate": (cache_hits / total) if total else 0,
        "last_base": last_base,
        "git": git_info,
    }


def cmd_dashboard() -> int:
    payload = _dashboard_payload()
    type_counts = payload["types"]
    last = payload["last"]
    slowest = payload["slowest"]
    fail_summary = payload["failures"]
    last_base = payload["last_base"]
    if getattr(cmd_dashboard, "as_json", False):
        print(json.dumps(payload, indent=2))
        return 0
    if getattr(cmd_dashboard, "as_html", False):
        html = "<html><body><h2>Dashboard</h2>"
        html += "<h3>Project types</h3><ul>"
        for t, c in sorted(type_counts.items()):
            html += f"<li>{t}: {c}</li>"
        html += "</ul>"
        if payload.get("git"):
            g = payload["git"]
            html += f"<h3>Git</h3><ul><li>branch: {g.get('branch')}</li><li>dirty: {g.get('dirty_count')}</li><li>ahead/behind: {g.get('ahead','?')}/{g.get('behind','?')}</li></ul>"
        if last:
            html += f"<h3>Last run: {last.get('label','')}</h3><ul>"
            for r in last.get("results", []):
                status = "cached" if r.get("cached") else ("pass" if r.get("rc") == 0 else "fail")
                html += f"<li>{r.get('project')}: {status} ({r.get('duration',0):.2f}s)</li>"
            html += "</ul>"
        html += f"<p>Cache hit rate: {payload['cache_hit_rate']*100:.1f}%</p>"
        if last_base:
            html += f"<p>Last base: {last_base}</p>"
        html += "</body></html>"
        print(html)
        return 0
    if getattr(cmd_dashboard, "live", False):
        try:
            from rich.live import Live
            from rich.console import Group
            from rich.text import Text
            from rich.panel import Panel
            from rich.layout import Layout
            from time import sleep, monotonic
            interval = getattr(cmd_dashboard, "interval", 1.0)
            duration = getattr(cmd_dashboard, "duration", 0.0)
            with Live(refresh_per_second=4) as live:
                start = monotonic()
                while True:
                    payload = _dashboard_payload()
                    layout = Layout()
                    layout.split_row(
                        Layout(name="left"),
                        Layout(name="right")
                    )
                    # left: counts + meta
                    type_text = "\n".join([f"{t}: {c}" for t, c in sorted(payload["types"].items())]) or "n/a"
                    git_meta = ""
                    if payload.get("git"):
                        git_meta = f"Branch: {payload['git'].get('branch','?')}\nDirty: {payload['git'].get('dirty_count','?')}\nAhead/Behind: {payload['git'].get('ahead','?')}/{payload['git'].get('behind','?')}"
                        if payload["git"].get("dirty_files"):
                            git_meta += "\nDirty files:\n" + "\n".join(payload["git"]["dirty_files"])
                    meta = f"Cache hit: {payload['cache_hit_rate']*100:.1f}%\nLast base: {payload.get('last_base','')}"
                    git_panel = Panel(git_meta or "n/a", title="Git", border_style="yellow")
                    left_group = Group(
                        Panel(type_text, title="Types", border_style="cyan"),
                        Panel(meta, title="Meta", border_style="green"),
                        git_panel,
                    )
                    layout["left"].update(left_group)
                    # right: last run detail
                    panels = []
                    if payload["last"]:
                        rows = []
                        for r in payload["last"].get("results", []):
                            status = "cached" if r.get("cached") else ("pass" if r.get("rc") == 0 else "fail")
                            rows.append(f"{r.get('project')}: {status} ({r.get('duration',0):.2f}s)")
                        panels.append(Panel("\n".join(rows) or "n/a", title=f"Last: {payload['last'].get('label','')}", border_style="magenta"))
                    if payload["slowest"]:
                        slow_txt = "\n".join([f"{r.get('project')}: {r.get('duration',0):.2f}s" for r in payload["slowest"]])
                        panels.append(Panel(slow_txt, title="Slowest", border_style="yellow"))
                    if payload["failures"]:
                        fail_txt = "\n".join([f"{r.get('project')}: {r.get('duration',0):.2f}s" for r in payload["failures"]])
                        panels.append(Panel(fail_txt, title="Failures", border_style="red"))
                    if panels:
                        layout["right"].update(Group(*panels))
                    else:
                        layout["right"].update(Panel("n/a", title="Details"))
                    live.update(layout)
                    sleep(interval)
                    if duration > 0 and (monotonic() - start) >= duration:
                        break
            return 0
        except Exception:
            pass
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        console = Console()
        summary = Table(show_header=True, header_style="bold cyan")
        summary.add_column("type")
        summary.add_column("count", justify="right")
        for t, c in sorted(type_counts.items()):
            summary.add_row(t, str(c))
        console.print(Panel(summary, title="Projects", border_style="cyan"))
        if payload.get("git"):
            git_table = Table(title="Git", show_header=True, header_style="bold yellow")
            git_table.add_column("branch")
            git_table.add_column("dirty")
            git_table.add_column("ahead/behind")
            git_table.add_row(
                payload["git"].get("branch","?"),
                str(payload["git"].get("dirty_count","?")),
                f"{payload['git'].get('ahead','?')}/{payload['git'].get('behind','?')}",
            )
            if payload["git"].get("dirty_files"):
                git_table.add_row("dirty files", "\n".join(payload["git"]["dirty_files"]), "")
            console.print(git_table)
        if last:
            res_table = Table(show_header=True, header_style="bold magenta")
            res_table.add_column("project")
            res_table.add_column("status")
            res_table.add_column("duration", justify="right")
            for r in last.get("results", []):
                status = "cached" if r.get("cached") else ("pass" if r.get("rc") == 0 else "fail")
                style = "cyan" if status == "cached" else ("green" if r.get("rc") == 0 else "red")
                res_table.add_row(r.get("project", ""), f"[{style}]{status}[/{style}]", f"{r.get('duration', 0):.2f}s")
            console.print(Panel(res_table, title=f"Last run: {last.get('label','') or 'n/a'}"))
        if slowest:
            slow_table = Table(show_header=True, header_style="bold yellow")
            slow_table.add_column("project")
            slow_table.add_column("duration", justify="right")
            slow_table.add_column("status")
            for r in slowest:
                status = "cached" if r.get("cached") else ("pass" if r.get("rc") == 0 else "fail")
                slow_table.add_row(r.get("project",""), f"{r.get('duration',0):.2f}s", status)
            console.print(Panel(slow_table, title="Slowest (last run)"))
        if fail_summary:
            fail_table = Table(show_header=True, header_style="bold red")
            fail_table.add_column("project")
            fail_table.add_column("duration", justify="right")
            for r in fail_summary:
                fail_table.add_row(r.get("project",""), f"{r.get('duration',0):.2f}s")
            console.print(Panel(fail_table, title="Failures (last run)", border_style="red"))
        console.print(f"[dim]Cache hit rate (last run): {payload['cache_hit_rate']*100:.1f}%[/]")
        if last_base:
            console.print(f"[dim]Last base: {last_base}[/]")
        return 0
    except Exception:
        print("Projects by type:")
        for t, c in sorted(type_counts.items()):
            print(f"- {t}: {c}")
        if last:
            print(f"Last run: {last.get('label','')}")
            for r in last.get("results", []):
                status = "cached" if r.get("cached") else ("pass" if r.get("rc") == 0 else "fail")
                print(f"  - {r.get('project')}: {status} ({r.get('duration',0):.2f}s)")
        if slowest:
            print("Slowest (last run):")
            for r in slowest:
                print(f"  - {r.get('project')}: {r.get('duration',0):.2f}s")
        if fail_summary:
            print("Failures (last run):")
            for r in fail_summary:
                print(f"  - {r.get('project')}: {r.get('duration',0):.2f}s")
        print(f"Cache hit rate (last run): {payload['cache_hit_rate']*100:.1f}%")
        if last_base:
            print(f"Last base: {last_base}")
        return 0


def cmd_info(project: str) -> int:
    reg = load_registry()
    if project not in reg:
        print(f"[ma] project '{project}' not found in registry", file=sys.stderr)
        return 1
    entry = reg[project]
    # derive dependents
    dependents = [name for name, meta in reg.items() if project in meta.get("deps", [])]
    enriched = dict(entry)
    enriched["dependents"] = dependents
    # suggested smokes/watch
    enriched["suggested_smoke"] = "pipeline" if entry.get("type") in ("engine", "integration") else "full"
    enriched["suggested_watch"] = f"ma watch {project}"
    # doc link if exists
    doc_candidates = [
        ROOT / entry.get("path", "") / "README.md",
        ROOT / "docs" / f"{project}.md",
    ]
    docs = [str(p.relative_to(ROOT)) for p in doc_candidates if p.exists()]
    if docs:
        enriched["docs"] = docs
    # run/test commands from registry where present
    if entry.get("run"):
        enriched["run_cmd"] = entry["run"]
    if entry.get("tests"):
        enriched["test_cmd"] = [f"pytest {t}" for t in entry["tests"]]
    if not enriched.get("description"):
        enriched["description"] = "No description set in project_map.json"
    print(json.dumps(enriched, indent=2))
    return 0


def cmd_logs(tail: int) -> int:
    path = LOG_FILE
    if not path or not path.exists():
        print("[ma] no logs found (logging file missing or unwritable)")
        return 0
    try:
        lines = path.read_text().splitlines()[-tail:]
        for ln in lines:
            print(ln)
        return 0
    except Exception as exc:
        print(f"[ma] failed to read logs: {exc}", file=sys.stderr)
        return 1


PLAYBOOKS: Dict[str, List[str]] = {
    "pipeline-dev": [
        "python -m ma_helper doctor",
        "python -m ma_helper smoke pipeline",
    ],
    "host-dev": [
        "python -m ma_helper doctor",
        "python -m ma_helper smoke full",
    ],
    "sidecar-dev": [
        "python -m ma_helper doctor",
        "python -m ma_helper watch audio_engine",
    ],
}

PROFILES: Dict[str, Dict[str, Any]] = {
    "dev": {"sparse": ["hosts", "shared", "tools"], "playbook": "host-dev"},
    "pipeline": {"playbook": "pipeline-dev"},
    "minimal": {"sparse": ["shared", "tools"]},
}


def cmd_playbook(name: str, dry_run: bool) -> int:
    # load overrides from playbooks.yml if present
    yml = ROOT / "tools" / "ma_helper" / "playbooks.yml"
    if yml.exists():
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(yml.read_text()) or {}
            pb = data.get("playbooks", {})
            if isinstance(pb, dict):
                for k, v in pb.items():
                    if isinstance(v, list):
                        PLAYBOOKS[k] = v
        except Exception:
            pass
    cmds = PLAYBOOKS.get(name)
    if not cmds:
        print(f"[ma] unknown playbook {name}", file=sys.stderr)
        return 1
    print(f"[ma] playbook {name}:")
    for c in cmds:
        if dry_run:
            print(f" - {c}")
        else:
            rc = _run_cmd(c)
            if rc != 0:
                return rc
    return 0


def cmd_registry(args) -> int:
    reg = load_registry()
    path = ROOT / "project_map.json"
    if args.reg_action == "list":
        for name in reg.keys():
            print(name)
        return 0
    if args.reg_action == "show":
        if args.project not in reg:
            print(f"[ma] project '{args.project}' not found", file=sys.stderr)
            return 1
        print(json.dumps(reg[args.project], indent=2))
        return 0
    if args.reg_action == "validate":
        ok = True
        missing_paths = []
        missing_tests = []
        for name, entry in reg.items():
            pth = ROOT / entry.get("path", "")
            if not pth.exists():
                ok = False
                missing_paths.append((name, str(pth)))
            for t in entry.get("tests", []):
                tpath = ROOT / t
                if not tpath.exists():
                    ok = False
                    missing_tests.append((name, str(tpath)))
        if missing_paths or missing_tests:
            try:
                from rich.console import Console
                from rich.table import Table
                console = Console()
                if missing_paths:
                    table = Table(title="Missing paths", show_header=True, header_style="bold red")
                    table.add_column("project")
                    table.add_column("path")
                    for name, pth in missing_paths:
                        table.add_row(name, pth)
                    console.print(table)
                if missing_tests:
                    table = Table(title="Missing tests", show_header=True, header_style="bold red")
                    table.add_column("project")
                    table.add_column("test path")
                    for name, pth in missing_tests:
                        table.add_row(name, pth)
                    console.print(table)
            except Exception:
                for name, pth in missing_paths:
                    print(f"[warn] {name}: path missing -> {pth}")
                for name, pth in missing_tests:
                    print(f"[warn] {name}: tests missing -> {pth}")
            return 1
        print("[ma] registry ok")
        return 0
    if args.reg_action == "lint":
        sorted_reg = dict(sorted(reg.items(), key=lambda kv: kv[0]))
        print(json.dumps(sorted_reg, indent=2))
        if args.fix:
            path.write_text(json.dumps(sorted_reg, indent=2))
            print("[ma] registry normalized and written")
        return 0
    if args.reg_action == "add":
        new_entry = {
            "path": args.path,
            "tests": args.tests,
            "description": "",
            "type": args.type,
            "deps": [],
        }
        if args.run:
            new_entry["run"] = args.run
        print(f"[ma] add entry: {args.name} -> {new_entry}")
        if not args.yes:
            print("[ma] dry-run only (pass --yes to apply)")
            return 0
        reg[args.name] = new_entry
        path.write_text(json.dumps(reg, indent=2))
        print("[ma] registry updated")
        return 0
    if args.reg_action == "remove":
        if args.name not in reg:
            print(f"[ma] project '{args.name}' not found", file=sys.stderr)
            return 1
        print(f"[ma] removing {args.name}")
        if not args.yes:
            print("[ma] dry-run only (pass --yes to apply)")
            return 0
        if guard_level() == "strict" and not require_confirm(f"Remove {args.name} from registry?"):
            print("[ma] aborted (strict guard).")
            return 1
        reg.pop(args.name, None)
        path.write_text(json.dumps(reg, indent=2))
        print("[ma] registry updated")
        return 0
    return 1


def cmd_profile(args) -> int:
    if args.action == "list":
        for name in PROFILES:
            print(f"- {name}")
        return 0
    if args.action == "show":
        prof = PROFILES.get(args.name)
        if not prof:
            print(f"[ma] unknown profile {args.name}", file=sys.stderr)
            return 1
        print(json.dumps(prof, indent=2))
        return 0
    if args.action == "apply":
        prof = PROFILES.get(args.name)
        if not prof:
            print(f"[ma] unknown profile {args.name}", file=sys.stderr)
            return 1
        print(f"[ma] applying profile {args.name}")
        # sparse
        if prof.get("sparse"):
            print(f"[ma] sparse set -> {prof['sparse']}")
            rc = cmd_sparse(argparse.Namespace(set=prof["sparse"], reset=False, list=False))
            if rc != 0 and not args.ignore_errors:
                return rc
        # playbook
        if prof.get("playbook"):
            pb = prof["playbook"]
            print(f"[ma] running playbook {pb}")
            rc = cmd_playbook(pb, args.dry_run or DRY_RUN)
            if rc != 0 and not args.ignore_errors:
                return rc
        print("[ma] profile applied")
        return 0
    return 1


def cmd_git_branch(args) -> int:
    if shutil.which("git") is None:
        print("[ma] git not found; install git to create branches.", file=sys.stderr)
        return 1
    if not (ROOT / ".git").exists():
        print("[ma] no .git directory; run inside the repo.", file=sys.stderr)
        return 1
    # check clean tree
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
        if res.stdout.strip():
            print("[ma] working tree is dirty; commit/stash before creating a branch.", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[ma] git status failed: {exc}", file=sys.stderr)
        return 1
    # branch name suggestion
    desc = args.desc or "work"
    branch = f"{args.prefix}/{args.project}-{desc}".replace(" ", "-")
    print(f"[ma] creating branch {branch}")
    rc = subprocess.call(["git", "checkout", "-b", branch], cwd=ROOT)
    if rc != 0:
        return rc
    if args.upstream:
        subprocess.call(["git", "push", "--set-upstream", args.upstream, branch], cwd=ROOT)
    if args.sparse:
        print(f"[ma] applying sparse preset for {args.project}")
        paths = args.sparse
        cmd_sparse(argparse.Namespace(set=paths, reset=False, list=False))
    return 0


def _git_basic_status():
    info = {}
    try:
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        info["branch"] = res.stdout.strip()
    except Exception:
        info["branch"] = "unknown"
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
        dirty = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
        info["dirty"] = dirty
    except Exception:
        info["dirty"] = []
    try:
        res = subprocess.run(["git", "rev-list", "--left-right", "--count", "origin/main...HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        ahead, behind = res.stdout.strip().split()
        info["ahead"] = ahead
        info["behind"] = behind
    except Exception:
        info["ahead"] = info["behind"] = "?"
    return info


def cmd_git_status(args) -> int:
    info = _git_basic_status()
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    print(f"branch: {info.get('branch')}")
    print(f"ahead/behind vs origin/main: {info.get('ahead','?')}/{info.get('behind','?')}")
    if info.get("dirty"):
        print("dirty files:")
        for d in info["dirty"][:20]:
            print(f" - {d}")
        if len(info["dirty"]) > 20:
            print(" ... (truncated)")
    else:
        print("clean tree")
    return 0


def cmd_git_upstream(args) -> int:
    branch = args.branch
    if not branch:
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
            branch = res.stdout.strip()
        except Exception:
            print("[ma] unable to determine current branch", file=sys.stderr)
            return 1
    cmd = ["git", "push", "--set-upstream", args.remote, branch]
    print(f"[ma] {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=ROOT)


def cmd_git_rebase(args) -> int:
    if os.environ.get("MA_REQUIRE_CONFIRM") == "1" or guard_level() == "strict":
        if not require_confirm(f"Rebase current branch onto {args.onto}?"):
            return 1
    return subprocess.call(["git", "rebase", args.onto], cwd=ROOT)


def cmd_git_pull_check(args) -> int:
    # clean tree check
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
        if res.stdout.strip():
            print("[ma] dirty tree; commit/stash before pulling.", file=sys.stderr)
            return 1
    except Exception:
        print("[ma] warning: unable to check status; proceeding", file=sys.stderr)
    branch = args.branch
    if not branch:
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
            branch = res.stdout.strip()
        except Exception:
            branch = "HEAD"
    cmd = ["git", "pull", args.remote, branch]
    print(f"[ma] {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=ROOT)

def cmd_cache(args) -> int:
    if args.action == "stats":
        cache = load_cache()
        entries = len(cache)
        hashes = sum(1 for v in cache.values() for k in v if k.endswith("_hash"))
        print(f"[ma] cache entries: {entries}; hash slots: {hashes}")
        if CACHE_FILE.exists():
            print(f"[ma] cache file: {CACHE_FILE}")
        if ARTIFACT_DIR.exists():
            arts = list(ARTIFACT_DIR.glob("*.json"))
            print(f"[ma] artifacts: {len(arts)} ({ARTIFACT_DIR})")
        return 0
    if args.action == "clean":
        if guard_level() == "strict" and not require_confirm("Clean cache (.ma_cache)?"):
            print("[ma] aborted (strict guard).")
            return 1
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
        print("[ma] cache cleared")
        return 0
    if args.action == "list-artifacts":
        if not ARTIFACT_DIR.exists():
            print("[ma] no artifacts yet")
            return 0
        for p in ARTIFACT_DIR.glob("*.json"):
            print(p.name)
        return 0
    if args.action == "show-artifact":
        path = ARTIFACT_DIR / f"{args.name}.json"
        if not path.exists():
            print(f"[ma] artifact not found: {path}", file=sys.stderr)
            return 1
        print(path.read_text())
        return 0
    print("[ma] unknown cache action")
    return 1


def cmd_tour() -> int:
    try:
        from rich.console import Console
        from rich.prompt import Confirm
        console = Console()
        console.print("[bold cyan]Welcome to the monorepo helper tour[/bold cyan]")
        git_ok = shutil.which("git") is not None and (ROOT / ".git").exists()
        if Confirm.ask("Run doctor now?", default=True):
            cmd_doctor()
        if Confirm.ask("Show map overview?", default=True):
            cmd_map("ansi", None, False)
        if Confirm.ask("Show playbooks?", default=True):
            for name in PLAYBOOKS.keys():
                console.print(f"- {name}")
        if Confirm.ask("List smokes?", default=True):
            cmd_smoke("menu")
        if git_ok and Confirm.ask("Apply sparse preset for host-dev?", default=False):
            cmd_sparse(argparse.Namespace(set=["hosts", "shared", "tools"], reset=False, list=False))
        elif not git_ok:
            console.print("[dim]Skipping sparse prompt (no git/.git detected).[/]")
        if Confirm.ask("Run pipeline smoke? (requires env + data)", default=False):
            rc = cmd_smoke("pipeline")
            if rc != 0:
                console.print("[red]Pipeline smoke failed (see output); check PYTHONPATH/venv/data.[/]")
        console.print("[dim]Tip: set an alias like `alias ma=\"python -m ma_helper\"` for quick access.[/]")
        return 0
    except Exception:
        print("Tour: run doctor, map, playbooks, smokes interactively. Install rich for a nicer tour experience.")
        return 0

def cmd_completion(shell: str) -> int:
    """Emit a simple completion script for bash/zsh."""
    cmds = [
        "list","tasks","test","test-all","affected","run","deps","select","watch","ci-plan","info","playbook","shell",
        "registry","map","dashboard","tui","doctor","check","guard","preflight","github-check","hook","precommit",
        "chat-dev","git-branch","git-status","git-upstream","git-rebase","git-pull-check","welcome","help",
        "quickstart","tour","palette","sparse","scaffold","smoke","verify","ci-env","lint","typecheck","format",
        "rerun-last","history","logs","cache","favorites","profile","completion"
    ]
    if shell == "bash":
        words = " ".join(cmds)
        print(f'''_ma_helper() {{
    local cur prev
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "{words}" -- "$cur") )
        return 0
    fi
}}
complete -F _ma_helper ma_helper
complete -F _ma_helper ma
''')
    else:  # zsh
        words = " ".join(cmds)
        print(f'''#compdef ma ma_helper
_ma_helper() {{
  local -a cmds
  cmds=({words})
  _arguments "1:command:->cmds" "*::arg:->args"
  case $state in
    cmds) _describe 'command' cmds ;;
  esac
}}
_ma_helper "$@"
''')
    return 0

def cmd_shell(with_dash: bool = False, interval: float = 1.0) -> int:
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
        from prompt_toolkit.patch_stdout import patch_stdout
    except Exception:
        prompt = None  # type: ignore
        patch_stdout = None  # type: ignore
    # Fuzzy prompts via prompt_toolkit when available (if dash is on, still allow prompt_toolkit now that dash is separate pane).

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
            main(tokens)
        except SystemExit:
            # avoid exiting the shell
            pass
        finally:
            if with_dash:
                print_status()


def cmd_tui(interval: float, duration: int) -> int:
    """Split-pane Rich TUI: dashboard + last results + tips."""
    try:
        from rich.live import Live
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.table import Table
        from time import sleep, time as now
        from rich.console import Group
    except Exception:
        print("[ma] Rich not available; install `rich` for the TUI.")
        return 1
    start = now()
    with Live(refresh_per_second=8, screen=True):
        while now() - start < duration:
            payload = _dashboard_payload()
            layout = Layout()
            layout.split_column(
                Layout(name="top", ratio=2),
                Layout(name="bottom", ratio=1),
            )
            layout["top"].split_row(Layout(name="left"), Layout(name="right"))
            # left: types + meta
            type_text = "\n".join([f"{t}: {c}" for t, c in sorted(payload["types"].items())]) or "n/a"
            git_meta = ""
            if payload.get("git"):
                git_meta = f"Branch: {payload['git'].get('branch','?')}\nDirty: {payload['git'].get('dirty_count','?')}\nAhead/Behind: {payload['git'].get('ahead','?')}/{payload['git'].get('behind','?')}"
                if payload["git"].get("dirty_files"):
                    git_meta += "\nDirty files:\n" + "\n".join(payload["git"]["dirty_files"])
            meta = f"Cache hit: {payload['cache_hit_rate']*100:.1f}%\nLast base: {payload.get('last_base','')}"
            left_group = Group(
                Panel(type_text, title="Types", border_style="cyan"),
                Panel(meta, title="Meta", border_style="green"),
                Panel(git_meta or "n/a", title="Git", border_style="yellow"),
            )
            layout["left"].update(left_group)
            # right: last results
            last = payload.get("last") or {}
            results = last.get("results", [])
            tbl = Table(title=f"Last run: {last.get('label','') or 'n/a'}", show_header=True, header_style="bold magenta")
            tbl.add_column("project")
            tbl.add_column("status")
            tbl.add_column("duration", justify="right")
            if results:
                for r in results:
                    status = "cached" if r.get("cached") else ("pass" if r.get("rc") == 0 else "fail")
                    style = "cyan" if status == "cached" else ("green" if r.get("rc") == 0 else "red")
                    tbl.add_row(r.get("project",""), f"[{style}]{status}[/{style}]", f"{r.get('duration',0):.2f}s")
            else:
                tbl.add_row("n/a", "n/a", "0.00s")
            layout["right"].update(tbl)
            # bottom: tips
            tips = "\n".join([
                "q / Ctrl+C to exit",
                "ma shell  -> interactive commands",
                "ma verify -> lint+type+smoke+affected",
                "ma dashboard --live --interval 0.5 -> quick view",
                "ma guard --set strict -> confirmations for risky actions",
            ])
            layout["bottom"].update(Panel(tips, title="Tips", border_style="green"))
            Live.get().update(layout)
            sleep(interval)
    return 0
def _print_summary(results, title: str = "Summary") -> None:
    if not results:
        return
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        console = Console()
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("project", style="cyan")
        table.add_column("status", style="magenta")
        table.add_column("duration", justify="right")
        for item in results:
            status = "pass" if item["rc"] == 0 else "fail"
            status_style = "green" if item["rc"] == 0 else "red"
            dur = f'{item.get("duration", 0):.2f}s'
            label = status
            if item.get("cached"):
                label = "cached"
                status_style = "cyan"
            table.add_row(item["project"], f"[{status_style}]{label}[/{status_style}]", dur)
        console.print(Panel(table, title=title, border_style="cyan"))
    except Exception:
        print(f"{title}:")
        for item in results:
            status = "pass" if item["rc"] == 0 else "fail"
            if item.get("cached"):
                status = "cached"
            dur = f'{item.get("duration", 0):.2f}s'
            print(f"- {item['project']}: {status} ({dur})")


def record_results(results: List[Dict[str, Any]], label: str) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"label": label, "ts": time.time(), "results": results}
        LAST_RESULTS_FILE.write_text(json.dumps(payload, indent=2))
    except Exception:
        pass


def run_projects_parallel(projects, names, max_workers: int, cache_mode: str = "off", retries: int = 0):
    failures = []
    results = []
    def _run(name: str) -> tuple[str, int, float, Dict[str, Any]]:
        project = projects[name]
        skip, info = should_skip_cached(project, "test", cache_mode)
        if skip:
            return name, 0, 0.0, {"cached": True}
        start = time.time()
        rc = orch.run_tests_for_project(project)
        for _ in range(retries):
            if rc == 0:
                break
            rc = orch.run_tests_for_project(project)
        info["hash"] = hash_project(project)
        update_cache(project, "test", info, cache_mode)
        if cache_mode != "off" and rc == 0:
            write_artifact(project, "test", info)
        return name, rc, time.time() - start, info
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        for name, rc, dur, info in pool.map(_run, names):
            entry = {"project": name, "rc": rc, "duration": dur}
            entry.update(info)
            results.append(entry)
            if rc != 0:
                failures.append(name)
    return (0 if not failures else 1), results


def run_projects_serial(projects, names, cache_mode: str = "off", retries: int = 0):
    results = []
    failures = []
    for name in names:
        project = projects[name]
        skip, info = should_skip_cached(project, "test", cache_mode)
        if skip:
            results.append({"project": name, "rc": 0, "duration": 0.0, "cached": True})
            continue
        start = time.time()
        rc = orch.run_tests_for_project(project)
        for _ in range(retries):
            if rc == 0:
                break
            rc = orch.run_tests_for_project(project)
        info["hash"] = hash_project(project)
        update_cache(project, "test", info, cache_mode)
        if cache_mode != "off" and rc == 0:
            write_artifact(project, "test", info)
        entry = {"project": name, "rc": rc, "duration": time.time() - start}
        entry.update(info)
        results.append(entry)
        if rc != 0:
            failures.append(name)
    return (0 if not failures else 1), results


def compute_affected(projects, base: str, no_diff: bool):
    if no_diff:
        names = [n for n, p in projects.items() if p.tests]
        return names, [], "no-diff"
    return _collect_and_match_changes(projects, base, since=None, merge_base=False)


def _collect_and_match_changes(projects, base: str, since: str | None, merge_base: bool):
    changes = collect_changes(base, merge_base=merge_base, since=since)
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


def collect_changes(base: str, merge_base: bool = False, since: str | None = None) -> List[str]:
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
            mb = subprocess.run(["git", "merge-base", ref, "HEAD"], cwd=orch.ROOT, text=True, capture_output=True, check=True).stdout.strip()
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


def topo_sort(projects, names: List[str]) -> List[str]:
    deps_map = {n: set(projects[n].deps) for n in names if n in projects}
    ordered: List[str] = []
    temp = set()
    perm = set()

    def visit(node: str):
        if node in perm:
            return
        if node in temp:
            return  # ignore cycles gracefully
        temp.add(node)
        for dep in deps_map.get(node, []):
            if dep in deps_map:
                visit(dep)
        perm.add(node)
        ordered.append(node)

    for n in names:
        visit(n)
    # keep original order for unknowns
    seen = set(ordered)
    ordered += [n for n in names if n not in seen]
    return ordered


def emit_graph(projects, fmt: str) -> int:
    if fmt == "mermaid":
        print("graph TD")
        for name, proj in projects.items():
            if not proj.deps:
                continue
            for dep in proj.deps:
                print(f"  {dep} --> {name}")
        return 0
    if fmt in ("dot", "svg"):
        dot_lines = ["digraph G {"] + [
            f'  "{dep}" -> "{name}";'
            for name, proj in projects.items()
            for dep in proj.deps
        ] + ["}"]
        if fmt == "svg":
            if shutil.which("dot") is None:
                print("[ma] graphviz dot not found; install graphviz or use --graph dot/mermaid/text.", file=sys.stderr)
                return 1
            proc = subprocess.run(["dot", "-Tsvg"], input="\n".join(dot_lines), text=True, capture_output=True)
            if proc.returncode != 0:
                print(proc.stderr, file=sys.stderr)
                return proc.returncode
            svg_out = proc.stdout
            print(svg_out)
            if shutil.which("open") and fmt == "svg":
                # write temp file for convenience
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".svg")
                tmp.write(svg_out.encode("utf-8"))
                tmp.close()
                if getattr(emit_graph, "open_svg", False):
                    subprocess.call(["open", tmp.name])
            return 0
        print("\n".join(dot_lines))
        return 0
    if fmt == "ansi":
        for name, proj in projects.items():
            for dep in proj.deps:
                print(f"{dep} -> {name}")
        return 0
    for name, proj in projects.items():
        deps = ", ".join(proj.deps) if proj.deps else "none"
        print(f"{name}: {deps}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Music Advisor helper CLI (Nx/Turbo style UX)")
    p.add_argument("--dry-run", action="store_true", help="Print commands without executing shell calls where supported")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List projects")

    tasks_p = sub.add_parser("tasks", help="Show common tasks/aliases")
    tasks_p.add_argument("--filter", help="Filter tasks by substring")
    tasks_p.add_argument("--json", action="store_true", help="Output tasks as JSON")

    test_p = sub.add_parser("test", help="Test a project")
    test_p.add_argument("project", help="Project name")
    test_p.add_argument("--cache", choices=["off", "local", "restore-only"], default="off", help="Cache mode: off|local|restore-only")
    test_p.add_argument("--retries", type=int, default=0, help="Retry count on failure")
    test_p.add_argument("--require-preflight", action="store_true", help="Run preflight first and abort on failure")

    ta_p = sub.add_parser("test-all", help="Run all tests")
    ta_p.add_argument("--parallel", type=int, default=0, help="Run tests in parallel (workers; 0=serial)")
    ta_p.add_argument("--cache", choices=["off", "local", "restore-only"], default="off", help="Skip unchanged projects (hash-based cache)")
    ta_p.add_argument("--retries", type=int, default=0, help="Retry count on failure")
    ta_p.add_argument("--require-preflight", action="store_true", help="Run preflight first and abort on failure")

    aff_p = sub.add_parser("affected", help="Run affected tests vs base")
    aff_p.add_argument("--base", default="origin/main", help="Git base ref (default: origin/main)")
    aff_p.add_argument("--parallel", type=int, default=0, help="Run tests in parallel (workers; 0=serial)")
    aff_p.add_argument("--no-diff", action="store_true", help="Skip git diff and run all project tests")
    aff_p.add_argument("--base-from", choices=["last"], help="Reuse last base from config if available")
    aff_p.add_argument("--cache", choices=["off", "local", "restore-only"], default="off", help="Skip unchanged projects (hash-based cache)")
    aff_p.add_argument("--since", help="Use commits since <date/ref> instead of a base ref (git log --since)")
    aff_p.add_argument("--merge-base", action="store_true", help="Diff against merge-base(base, HEAD) for accuracy")
    aff_p.add_argument("--retries", type=int, default=0, help="Retry count on failure")
    aff_p.add_argument("--require-preflight", action="store_true", help="Run preflight first and abort on failure")

    run_p = sub.add_parser("run", help="Run a project target (if configured)")
    run_p.add_argument("project", help="Project name or project:target (targets: run|test)")

    deps_p = sub.add_parser("deps", help="Show dependencies")
    deps_p.add_argument("--reverse", action="store_true", help="Show dependents instead")
    deps_p.add_argument("--graph", choices=["text", "mermaid", "dot", "svg", "ansi"], default="text", help="Graph format")
    deps_p.add_argument("--open", action="store_true", help="Open SVG output (if using --graph svg and dot available)")

    sub.add_parser("select", help="Interactive picker (test/run/deps/affected/watch)")

    watch_p = sub.add_parser("watch", help="Watch a project and rerun tests on change (uses entr or watchfiles)")
    watch_p.add_argument("project", help="Project to watch")
    watch_p.add_argument("--cmd", help="Override command to run on change (default: project test)")
    watch_p.add_argument("--on-success", help="Command to run after a successful run")
    watch_p.add_argument("--on-fail", help="Command to run after a failed run")
    watch_p.add_argument("--preset", choices=["test", "lint"], help="Use a preset command (overrides --cmd)")
    watch_p.add_argument("--rerun-last-failed", action="store_true", help="Run last failed command once before watching if recorded")
    watch_p.add_argument("--hotkeys", action="store_true", help="Enable simple hotkeys (r/f/q) when using watchfiles backend")
    watch_p.add_argument("--require-preflight", action="store_true", help="Run preflight first and abort on failure")

    ci_plan = sub.add_parser("ci-plan", help="Print affected projects without running tests (for CI wiring)")
    ci_plan.add_argument("--base", default="origin/main", help="Git base ref (default: origin/main)")
    ci_plan.add_argument("--commands", action="store_true", help="Emit shell commands for affected projects")
    ci_plan.add_argument("--matrix", action="store_true", help="Emit GitHub Actions-style matrix JSON")
    ci_plan.add_argument("--no-diff", action="store_true", help="Skip git diff; treat all projects as affected")
    ci_plan.add_argument("--gha", action="store_true", help="Emit a GitHub Actions job matrix snippet")
    ci_plan.add_argument("--base-from", choices=["last"], help="Reuse last base from config if available")
    ci_plan.add_argument("--since", help="Use commits since <date/ref> instead of a base ref (git log --since)")
    ci_plan.add_argument("--merge-base", action="store_true", help="Diff against merge-base(base, HEAD) for accuracy")
    ci_plan.add_argument("--targets", nargs="+", default=["test"], help="Targets to include (default: test)")
    ci_plan.add_argument("--gitlab", action="store_true", help="Emit a GitLab-style matrix payload")
    ci_plan.add_argument("--circle", action="store_true", help="Emit a CircleCI parameters-style payload")

    info = sub.add_parser("info", help="Show project info from registry")
    info.add_argument("project", help="Project name")

    playbook = sub.add_parser("playbook", help="Run or print preset flows")
    playbook.add_argument("name", choices=["pipeline-dev", "host-dev", "sidecar-dev"], help="Playbook name")
    playbook.add_argument("--dry-run", action="store_true", help="Print commands without running")

    shell_p = sub.add_parser("shell", help="Interactive REPL-style shell for helper commands")
    shell_p.add_argument("--dash", action="store_true", help="Show a pinned live dashboard while in shell (Rich)")
    shell_p.add_argument("--interval", type=float, default=1.0, help="Dashboard refresh interval when --dash is set (seconds)")

    comp = sub.add_parser("completion", help="Emit shell completion script")
    comp.add_argument("shell", choices=["bash", "zsh"], help="Target shell")

    registry = sub.add_parser("registry", help="Inspect or edit project_map.json")
    reg_sub = registry.add_subparsers(dest="reg_action", required=True)
    reg_sub.add_parser("list", help="List projects in registry")
    reg_show = reg_sub.add_parser("show", help="Show a project entry")
    reg_show.add_argument("project")
    reg_sub.add_parser("validate", help="Validate registry paths/tests")
    reg_lint = reg_sub.add_parser("lint", help="Normalize project_map.json (sorted keys)")
    reg_lint.add_argument("--fix", action="store_true", help="Write normalized file")
    reg_add = reg_sub.add_parser("add", help="Add project to registry")
    reg_add.add_argument("--name", required=True)
    reg_add.add_argument("--path", required=True)
    reg_add.add_argument("--tests", nargs="*", default=[])
    reg_add.add_argument("--type", default="misc")
    reg_add.add_argument("--run", nargs="*")
    reg_add.add_argument("--yes", action="store_true", help="Apply changes (otherwise dry-run)")
    reg_rm = reg_sub.add_parser("remove", help="Remove project from registry")
    reg_rm.add_argument("--name", required=True)
    reg_rm.add_argument("--yes", action="store_true", help="Apply changes (otherwise dry-run)")

    map_p = sub.add_parser("map", help="Show architectural map/topology")
    map_p.add_argument("--format", choices=["ansi", "mermaid", "dot", "svg", "html"], default="ansi")
    map_p.add_argument("--filter", help="Substring to filter projects")
    map_p.add_argument("--open", action="store_true", help="Open SVG/HTML (if generated)")

    dash = sub.add_parser("dashboard", help="Show a quick monorepo dashboard (counts, last results, base)")
    dash.add_argument("--json", action="store_true", help="Emit JSON")
    dash.add_argument("--html", action="store_true", help="Emit HTML")
    dash.add_argument("--live", action="store_true", help="Live refresh (Rich)")
    dash.add_argument("--interval", type=float, default=1.0, help="Live refresh interval seconds (default 1.0)")
    dash.add_argument("--duration", type=float, default=0.0, help="Seconds to run live (0 = until you quit)")

    tui = sub.add_parser("tui", help="Rich split-pane view (dashboard + last results)")
    tui.add_argument("--interval", type=float, default=1.0, help="Refresh interval seconds (default 1.0)")
    tui.add_argument("--duration", type=int, default=60, help="Seconds to run (default 60)")

    doctor = sub.add_parser("doctor", help="Check env/tools for the repo")
    doctor.add_argument("--require-optional", action="store_true", help="Fail if optional deps missing (rich/watchfiles/entr/graphviz)")
    sub.add_parser("check", help="Quick repo sanity check (git dirty, venv, watch deps)")
    guard = sub.add_parser("guard", help="Show or set guard level (normal|strict)")
    guard.add_argument("--set", choices=["normal", "strict"])

    sub.add_parser("preflight", help="Check registry test/run paths exist")
    gh_check = sub.add_parser("github-check", help="Pre-push/pre-CI readiness (clean tree, branch, preflight, verify)")
    gh_check.add_argument("--require-branch", help="Require current branch name (e.g. main)")
    gh_check.add_argument("--require-clean", action="store_true", help="Fail if working tree is dirty")
    gh_check.add_argument("--preflight", action="store_true", help="Run preflight (missing paths) and fail on error")
    gh_check.add_argument("--verify", action="store_true", help="Run verify gate and fail on error")
    gh_check.add_argument("--ci-plan", action="store_true", help="Show affected matrix (ci-plan) vs base")
    gh_check.add_argument("--base", default="origin/main", help="Base ref for ci-plan (default origin/main)")
    gh_check.add_argument("--require-optional", action="store_true", help="Require optional deps (rich/watchfiles/entr/graphviz)")
    gh_check.add_argument("--require-clean-env", action="store_true", help="Respect MA_REQUIRE_CLEAN env if set")
    gh_check.add_argument("--require-upstream", action="store_true", help="Fail if no upstream tracking branch is set")

    hook = sub.add_parser("hook", help="Git hook helper (pre-push)")
    hook.add_argument("name", choices=["pre-push"], help="Hook name")
    hook.add_argument("--install", action="store_true", help="Write hook file into .git/hooks")

    precommit = sub.add_parser("precommit", help="Git pre-commit hook helper")
    precommit.add_argument("action", choices=["print", "install"], help="Print or install pre-commit hook")
    chatdev = sub.add_parser("chat-dev", help="Backend-only chat dev helper (tmux layout or printed commands)")
    chatdev.add_argument("--log-file", default="logs/chat.log", help="Log/payload file to tail (default logs/chat.log)")
    chatdev.add_argument("--endpoint", default="http://127.0.0.1:8000/chat", help="Chat endpoint URL for tools/chat_cli.py")

    git_branch = sub.add_parser("git-branch", help="Create a project-focused branch with optional sparse setup")
    git_branch.add_argument("project", help="Project name to include in branch name")
    git_branch.add_argument("--desc", help="Short description for branch name", default="work")
    git_branch.add_argument("--prefix", default="feature", help="Branch prefix (default: feature)")
    git_branch.add_argument("--upstream", help="Push and set upstream to this remote (optional)")
    git_branch.add_argument("--sparse", nargs="+", help="Sparse paths to set after branch creation (optional)")

    git_status = sub.add_parser("git-status", help="Short git status (branch, dirty, ahead/behind)")
    git_status.add_argument("--json", action="store_true", help="Emit JSON")

    git_upstream = sub.add_parser("git-upstream", help="Set upstream for current branch")
    git_upstream.add_argument("--remote", default="origin", help="Remote name (default origin)")
    git_upstream.add_argument("--branch", default=None, help="Branch name (default: current)")

    git_rebase = sub.add_parser("git-rebase", help="Safe rebase helper")
    git_rebase.add_argument("--onto", default="origin/main", help="Target to rebase onto (default origin/main)")

    git_pull_check = sub.add_parser("git-pull-check", help="Ensure clean tree before pulling")
    git_pull_check.add_argument("--remote", default="origin", help="Remote (default origin)")
    git_pull_check.add_argument("--branch", default=None, help="Branch (default current)")

    sub.add_parser("welcome", help="Show a guided overview of the helper and common commands")
    sub.add_parser("help", help="Command palette style help for the helper")
    sub.add_parser("quickstart", help="Print the top helper commands to run first")
    sub.add_parser("tour", help="Interactive tour (rich if available)")
    sub.add_parser("palette", help="Print a compact palette of common commands")

    sparse = sub.add_parser("sparse", help="Git sparse-checkout helpers")
    sparse.add_argument("--set", nargs="+", help="Paths to include (cone mode)")
    sparse.add_argument("--reset", action="store_true", help="Disable sparse-checkout")
    sparse.add_argument("--list", action="store_true", help="Show current sparse paths")

    scaffold = sub.add_parser("scaffold", help="Scaffold a new project skeleton (safe defaults)")
    scaffold.add_argument("--type", choices=["engine", "host", "shared"], required=True, help="Project type")
    scaffold.add_argument("--name", required=True, help="Project name (folder)")
    scaffold.add_argument("--path", help="Destination path (default: tools/scaffolds/<name>)")
    scaffold.add_argument("--write-registry", action="store_true", help="Also add to project_map.json (sorted)")

    smoke = sub.add_parser("smoke", help="Run predefined smokes")
    smoke.add_argument("target", choices=["pipeline", "full", "menu"], help="Which smoke to run")

    verify = sub.add_parser("verify", help="Run a short gate: lint + typecheck + smoke + affected(no-diff)")
    verify.add_argument("--ignore-failures", action="store_true", help="Continue even if a step fails")
    verify.add_argument("--require-preflight", action="store_true", help="Run preflight first and abort on failure")

    sub.add_parser("ci-env", help="Print env var hints for CI jobs")

    lint = sub.add_parser("lint", help="Run lint (delegates to repo scripts/ruff)")
    typec = sub.add_parser("typecheck", help="Run typecheck (delegates to repo scripts/mypy)")
    fmt = sub.add_parser("format", help="Format code (ruff format if available)")

    rerun = sub.add_parser("rerun-last", help="Rerun the last command recorded in history")
    history = sub.add_parser("history", help="Show recent history")
    history.add_argument("--limit", type=int, default=10, help="Number of entries to show (default 10)")

    logs_p = sub.add_parser("logs", help="Tail helper logs")
    logs_p.add_argument("--tail", type=int, default=50, help="How many lines to show (default 50)")

    cache = sub.add_parser("cache", help="Cache controls")
    cache_sub = cache.add_subparsers(dest="action", required=True)
    cache_sub.add_parser("stats", help="Show cache stats")
    cache_sub.add_parser("clean", help="Clean cache (hashes/results)")
    cache_sub.add_parser("list-artifacts", help="List artifact metadata files")
    cache_show = cache_sub.add_parser("show-artifact", help="Show artifact metadata by name (project_target)")
    cache_show.add_argument("--name", required=True, help="Artifact name (e.g., audio_engine_test)")

    fav_parent = sub.add_parser("favorites", help="Manage favorites/history")
    fav_sub = fav_parent.add_subparsers(dest="fav_action", required=True)
    fav_list = fav_sub.add_parser("list", help="List favorites/history")
    fav_list.add_argument("--json", action="store_true", help="JSON output")
    fav_add = fav_sub.add_parser("add", help="Add or replace a favorite")
    fav_add.add_argument("--name", required=True, help="Favorite name")
    fav_add.add_argument("--cmd", required=True, help="Command to save")
    fav_run = fav_sub.add_parser("run", help="Run a favorite by name")
    fav_run.add_argument("--name", required=True, help="Favorite name")

    profile = sub.add_parser("profile", help="Apply helper presets (sparse/playbooks)")
    prof_sub = profile.add_subparsers(dest="action", required=True)
    prof_sub.add_parser("list", help="List profiles")
    prof_show = prof_sub.add_parser("show", help="Show profile details")
    prof_show.add_argument("name")
    prof_apply = prof_sub.add_parser("apply", help="Apply a profile")
    prof_apply.add_argument("name")
    prof_apply.add_argument("--dry-run", action="store_true")
    prof_apply.add_argument("--ignore-errors", action="store_true", help="Continue even if a step fails")

    return p


def main(argv=None) -> int:
    projects = orch.load_projects()
    args = build_parser().parse_args(argv)
    dry_run = getattr(args, "dry_run", False)
    global DRY_RUN
    DRY_RUN = dry_run
    enforce_permissions(ROOT)  # warn-only
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

    if args.command == "list":
        rc = orch.list_projects(projects)
        _post_list_hint()
        return rc
    if args.command == "tasks":
        return cmd_tasks(getattr(args, "filter", None), getattr(args, "json", False))
    if args.command == "test":
        proj = orch.resolve_project_arg(projects, args.project, None)
        add_history(f"python tools/ma_orchestrator.py test {proj.name}")
        if dry_run:
            print(f"[ma] dry-run: would run tests for {proj.name}")
            return 0
        missing = [p for p in proj.tests if not (ROOT / p).exists()]
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
        _log_event({"cmd": f"test {proj.name}", "rc": rc})
        return rc
    if args.command == "test-all":
        names = topo_sort(projects, [n for n, p in projects.items() if p.tests])
        if dry_run:
            print(f"[ma] dry-run: would run tests for: {', '.join(names)}")
            return 0
        if args.parallel and args.parallel > 0:
            rc, results = run_projects_parallel(projects, names, args.parallel, getattr(args, "cache", "off"), getattr(args, "retries", 0))
            _print_summary(results, "test-all (parallel)")
        else:
            rc, results = run_projects_serial(projects, names, getattr(args, "cache", "off"), getattr(args, "retries", 0))
            _print_summary(results, "test-all")
        record_results(results, "test-all")
        _log_event({"cmd": "test-all", "rc": rc})
        return rc
    if args.command == "affected":
        base = resolve_base(args.base, getattr(args, "base_from", None))
        names, changes, mode = _collect_and_match_changes(projects, base, getattr(args, "since", None), getattr(args, "merge_base", False)) if not getattr(args, "no_diff", False) else compute_affected(projects, base, True)
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
            _post_affected_hint()
            return 0
        if args.parallel and args.parallel > 0:
            rc, results = run_projects_parallel(projects, names, args.parallel, getattr(args, "cache", "off"), getattr(args, "retries", 0))
            _print_summary(results, f"affected ({mode}, parallel)")
            _log_event({"cmd": f"affected --base {base}", "rc": rc})
            record_results(results, f"affected-{mode}")
            _post_affected_hint()
            return rc
        rc, results = run_projects_serial(projects, names, getattr(args, "cache", "off"), getattr(args, "retries", 0))
        _print_summary(results, f"affected ({mode})")
        _log_event({"cmd": f"affected --base {base}", "rc": rc})
        record_results(results, f"affected-{mode}")
        _post_affected_hint()
        return rc
    if args.command == "run":
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
            if first.startswith("./") and not (ROOT / first).exists():
                print(f"[ma] warning: run target entry not found: {first}", file=sys.stderr)
                if os.environ.get("MA_REQUIRE_CONFIRM") == "1" or guard_level() == "strict" or os.environ.get("MA_REQUIRE_SAFE_RUN") == "1":
                    if not require_confirm(f"Proceed running {proj.name} even though {first} is missing?"):
                        return 1
        if tgt == "run":
            add_history(f"python tools/ma_orchestrator.py run {proj.name}")
            rc = orch.run_project_target(proj)
            _log_event({"cmd": f"run {proj.name}", "rc": rc})
            return rc
        if tgt == "test":
            add_history(f"python tools/ma_orchestrator.py test {proj.name}")
            rc = orch.run_tests_for_project(proj)
            _log_event({"cmd": f"test {proj.name}", "rc": rc})
            return rc
        print(f"[ma] unknown target '{tgt}' for project '{proj.name}'", file=sys.stderr)
        return 1
    if args.command == "deps":
        if args.graph and args.graph != "text":
            return emit_graph(projects, args.graph)
        return orch.print_deps(projects, reverse=getattr(args, "reverse", False))
    if args.command == "select":
        return cmd_select(projects)
    if args.command == "watch":
        base_cmd = args.cmd or f"python3 tools/ma_orchestrator.py test {args.project}"
        add_history(f"watch {args.project}: {base_cmd}")
        if dry_run:
            print(f"[ma] dry-run: would watch {args.project} with cmd: {base_cmd}")
            return 0
        cmd_watch.on_success = getattr(args, "on_success", None)
        cmd_watch.on_fail = getattr(args, "on_fail", None)
        cmd_watch.preset = getattr(args, "preset", None)
        cmd_watch.rerun_last_failed = getattr(args, "rerun_last_failed", False)
        cmd_watch.hotkeys = getattr(args, "hotkeys", False)
        return cmd_watch(args.project, base_cmd)
    if args.command == "ci-plan":
        # optional enforcement: require clean tree if env set
        if os.environ.get("MA_REQUIRE_CLEAN") == "1":
            try:
                res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
                if res.stdout.strip():
                    print("[ma] git working tree is dirty; set MA_REQUIRE_CLEAN=0 to bypass.", file=sys.stderr)
                    return 1
            except Exception:
                print("[ma] warning: unable to check git status; proceeding.", file=sys.stderr)
        base = resolve_base(args.base, getattr(args, "base_from", None))
        changes = [] if args.no_diff else collect_changes(base, merge_base=getattr(args, "merge_base", False), since=getattr(args, "since", None))
        targets = args.targets
        def emit_matrix(names):
            entries = []
            for n in names:
                for t in targets:
                    cmd = f"python tools/ma_orchestrator.py test {n}" if t == "test" else f"python tools/ma_orchestrator.py run {n}"
                    entries.append({"project": n, "target": t, "cmd": cmd})
            return {"include": entries}
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
    if args.command == "favorites":
        if args.fav_action == "list":
            return list_favorites(getattr(args, "json", False))
        if args.fav_action == "add":
            ensure_favorite(args.name, args.cmd)
            print(f"[ma] saved favorite '{args.name}' -> {args.cmd}")
            return 0
        if args.fav_action == "run":
            data = load_favorites()
            cmd_entry = next((f for f in data.get("favorites", []) if f.get("name") == args.name), None)
            if not cmd_entry:
                print(f"[ma] favorite '{args.name}' not found", file=sys.stderr)
                return 1
            cmd = cmd_entry.get("cmd", "")
            if not cmd:
                print(f"[ma] favorite '{args.name}' has no command", file=sys.stderr)
                return 1
            print(f"[ma] running favorite '{args.name}': {cmd}")
            add_history(cmd)
            return subprocess.call(cmd, shell=True, cwd=orch.ROOT)
    if args.command == "doctor":
        return cmd_doctor(getattr(args, "require_optional", False))
    if args.command == "guard":
        return cmd_guard(args)
    if args.command == "check":
        return cmd_check()
    if args.command == "preflight":
        return cmd_preflight()
    if args.command == "github-check":
        return cmd_github_check(args)
    if args.command == "hook":
        return cmd_hook(args)
    if args.command == "precommit":
        return cmd_precommit(args)
    if args.command == "sparse":
        return cmd_sparse(args)
    if args.command == "scaffold":
        return cmd_scaffold(args)
    if args.command == "smoke":
        return cmd_smoke(args.target)
    if args.command == "verify":
        return cmd_verify(args)
    if args.command == "ci-env":
        return cmd_ci_env()
    if args.command == "lint":
        return cmd_lint()
    if args.command == "typecheck":
        return cmd_typecheck()
    if args.command == "format":
        return cmd_format()
    if args.command == "rerun-last":
        return cmd_rerun_last()
    if args.command == "welcome":
        return cmd_welcome()
    if args.command == "help":
        return cmd_help()
    if args.command == "quickstart":
        return cmd_quickstart()
    if args.command == "palette":
        return cmd_palette()
    if args.command == "history":
        return cmd_history(args.limit)
    if args.command == "info":
        return cmd_info(args.project)
    if args.command == "playbook":
        return cmd_playbook(args.name, args.dry_run)
    if args.command == "registry":
        return cmd_registry(args)
    if args.command == "map":
        if args.format == "svg" and args.open:
            emit_graph.open_svg = True
        return cmd_map(args.format, args.filter, args.open)
    if args.command == "dashboard":
        cmd_dashboard.as_json = getattr(args, "json", False)
        cmd_dashboard.as_html = getattr(args, "html", False)
        cmd_dashboard.live = getattr(args, "live", False)
        cmd_dashboard.interval = getattr(args, "interval", 1.0)
        cmd_dashboard.duration = getattr(args, "duration", 0.0)
        return cmd_dashboard()
    if args.command == "tui":
        return cmd_tui(getattr(args, "interval", 1.0), getattr(args, "duration", 60))
    if args.command == "tour":
        return cmd_tour()
    if args.command == "logs":
        return cmd_logs(args.tail)
    if args.command == "profile":
        return cmd_profile(args)
    if args.command == "cache":
        return cmd_cache(args)
    if args.command == "shell":
        return cmd_shell(with_dash=getattr(args, "dash", False), interval=getattr(args, "interval", 1.0))
    if args.command == "completion":
        return cmd_completion(args.shell)
    if args.command == "git-branch":
        return cmd_git_branch(args)
    if args.command == "chat-dev":
        return cmd_chat_dev(args)
    if args.command == "git-status":
        return cmd_git_status(args)
    if args.command == "git-upstream":
        return cmd_git_upstream(args)
    if args.command == "git-rebase":
        return cmd_git_rebase(args)
    if args.command == "git-pull-check":
        return cmd_git_pull_check(args)

    print(f"Unknown command {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
