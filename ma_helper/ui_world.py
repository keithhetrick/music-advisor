"""
Minimal theming helpers for ma_helper.

Provides a reusable banner and heading renderers to signal the Music Advisor
helper context. Uses rich when available; falls back to plain ASCII.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict


def _git_summary(root: Path) -> Dict[str, str]:
    summary = {"branch": "unknown", "dirty": "?"}
    if shutil.which("git") is None or not (root / ".git").exists():
        return summary
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        summary["branch"] = res.stdout.strip()
    except Exception:
        pass
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        summary["dirty"] = "dirty" if res.stdout.strip() else "clean"
    except Exception:
        pass
    return summary


def print_banner(root: Path, guard: str = "normal") -> None:
    summary = _git_summary(root)
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
    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        console.print(Panel("\n".join(banner_lines), border_style="cyan", style="bold"))
    except Exception:
        pass
    # Always emit a plain banner so users without rich still see it.
    print("\n".join(banner_lines))


def heading(text: str) -> None:
    """Print a simple heading with fallback."""
    try:
        from rich.console import Console
        from rich.rule import Rule

        console = Console()
        console.print(Rule(text, style="cyan"))
    except Exception:
        print(f"\n=== {text} ===")


def hint(text: str) -> None:
    """Print a hint/next-step line."""
    try:
        from rich.console import Console
        console = Console()
        console.print(f"[dim]{text}[/]")
    except Exception:
        print(text)
