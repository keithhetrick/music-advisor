"""UX/help/welcome commands."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Any

from ma_helper.core.state import guard_level
from ma_helper.core.env import ROOT
from ma_helper.core.git import git_summary
import os


def _git_mode() -> str:
    return os.environ.get("MA_GIT_MODE", "on")


def _status_line(summary) -> str:
    guard = guard_level()
    git_mode = _git_mode()
    branch = summary.get("branch", "?")
    dirty = summary.get("dirty", "?")
    ahead = summary.get("ahead", "?")
    behind = summary.get("behind", "?")
    upstream = summary.get("upstream", "none")
    return f"branch: {branch} | dirty: {dirty} | ahead/behind: {ahead}/{behind} | upstream: {upstream} | guard: {guard} | git: {git_mode}"


def print_ma_banner():
    """Print a short banner to signal the Music Advisor helper context."""
    summary = git_summary()
    status = _status_line(summary)
    try:
        from ma_helper.ui_world import print_banner
        print_banner(ROOT, guard_level(), summary)
    except Exception:
        content = [
            "Music Advisor Helper (monorepo tools)",
            "ma quickstart  → top commands",
            "ma welcome    → overview",
            "ma palette    → common ops",
            "ma list       → projects",
        ]
        width = max(len(status), *(len(line) for line in content)) + 4
        top = "╔" + "═" * (width - 2) + "╗"
        sep = "╠" + "═" * (width - 2) + "╣"
        bottom = "╚" + "═" * (width - 2) + "╝"
        banner_lines = [top] + [f"║ {line.ljust(width - 4)} ║" for line in content] + [sep, f"║ {status.ljust(width - 4)} ║", bottom]
        print("\n".join(banner_lines))


def maybe_first_run_hint(command: str, save_favorites, load_favorites) -> bool:
    """Lightweight first-run nudge; best-effort (ignore write errors). Returns True if banner was printed."""
    cfg = load_favorites()
    if cfg.get("onboarded"):
        return False
    cfg["onboarded"] = True
    try:
        save_favorites(cfg)
    except Exception:
        pass
    print_ma_banner()
    print("Welcome to the Music Advisor helper. Try: ma quickstart | ma welcome | ma palette | ma list")
    print(f"[ma] You ran: {command}")
    return True


def post_hint(message: str):
    try:
        from ma_helper.ui_world import hint
        hint(message)
    except Exception:
        pass


def post_list_hint():
    post_hint("Tip: ma select (picker) | ma map --format mermaid | ma dashboard")


def post_affected_hint():
    post_hint("Tip: ma verify | ma ci-plan --matrix | ma dashboard --live")


def post_verify_hint():
    post_hint("Tip: ma dashboard --html > /tmp/ma_dashboard.html | ma palette | ma doctor")


def post_dashboard_hint():
    post_hint("Tip: ma affected --base origin/main | ma verify | ma ci-plan --matrix")


def show_world(command: str | None = None) -> None:
    """Print the UI world banner if available, fallback to the ASCII banner."""
    try:
        from ma_helper.ui_world import print_banner
        print_banner(ROOT, guard_level())
    except Exception:
        print_ma_banner()


def render_header() -> None:
    """Render a one-line header; tries Rich, falls back to the ASCII banner."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        summary = git_summary()
        guard = guard_level()
        git_mode = _git_mode()
        branch = summary.get("branch", "?")
        dirty = summary.get("dirty", "?")
        ahead = summary.get("ahead", "?")
        behind = summary.get("behind", "?")
        upstream = summary.get("upstream", "none")
        color = "green" if dirty == "clean" else "yellow"
        text = (
            f"[bold cyan]Music Advisor[/] | branch: {branch} | state: [{color}]{dirty}[/{color}] | "
            f"ahead/behind: {ahead}/{behind} | upstream: {upstream} | guard: {guard} | git: {git_mode}"
        )
        Console().print(Panel(text, style="bold magenta", padding=(0, 1)))
        return
    except Exception:
        print_ma_banner()


def render_error_panel(message: str, suggestions: list[str] | None = None) -> None:
    """Render an error panel with optional suggestions; falls back to plain text."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        text = Text(message, style="bold red")
        if suggestions:
            text.append("\n\nSuggestions:\n", style="bold")
            for s in suggestions:
                text.append(f" - {s}\n")
        Console().print(Panel(text, style="red", padding=(1, 1)))
        return
    except Exception:
        print(f"[ma][error] {message}")
        if suggestions:
            print("Suggestions:")
            for s in suggestions:
                print(f" - {s}")


def render_hint_panel(title: str, hints: list[str]) -> None:
    """Render a hint panel (success/info) with Rich if available; fallback to text."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        body = "\n".join(f"- {h}" for h in hints)
        Console().print(Panel(body, title=title, style="green", padding=(0, 1)))
    except Exception:
        print(f"[ma] {title}")
        for h in hints:
            print(f"- {h}")


@contextmanager
def live_header(status_text_fn):
    """Context manager for a live header if Rich is available; no-op otherwise."""
    try:
        from rich.live import Live
        from rich.panel import Panel
        text = status_text_fn()
        panel = Panel(text, style="bold magenta", padding=(0, 1))
        console_live = Live(panel, refresh_per_second=4)
        console_live.start()

        def update():
            try:
                new_text = status_text_fn()
                console_live.update(Panel(new_text, style="bold magenta", padding=(0, 1)))
            except Exception:
                pass

        try:
            yield update
        finally:
            try:
                update()
            except Exception:
                pass
            console_live.stop()
    except Exception:
        yield lambda: None
