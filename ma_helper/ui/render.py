"""
Rich-based renderers for consistent premium CLI output.

Falls back to simple text when Rich is unavailable.
"""
from __future__ import annotations

from typing import Iterable, Mapping


def render_header_bar(status: Mapping[str, str]) -> None:
    """Render a single-line status bar. Falls back to plain print."""
    line = " | ".join(f"{k}: {v}" for k, v in status.items())
    try:
        from rich.console import Console
        from rich.panel import Panel

        Console().print(Panel(line, style="bold cyan", padding=(0, 1)))
    except Exception:
        print(line)


def render_task_summary(results: Iterable[Mapping[str, object]], title: str) -> None:
    """Render a task/test summary table with badges."""
    rows = list(results)
    try:
        from rich.console import Console
        from rich.table import Table

        table = Table(title=title, expand=True)
        table.add_column("project", style="bold")
        table.add_column("rc", justify="center")
        table.add_column("duration", justify="right")
        table.add_column("cached", justify="center")
        table.add_column("last", overflow="fold")
        for entry in rows:
            rc = entry.get("rc")
            rc_txt = "✅" if rc == 0 else "❌"
            dur = entry.get("duration", 0.0)
            cached = "hit" if entry.get("cached") else ""
            last = entry.get("last", "")
            table.add_row(entry.get("project", "?"), rc_txt, f"{dur:.1f}s", cached, last)
        Console().print(table)
    except Exception:
        print(title)
        for entry in rows:
            rc = entry.get("rc")
            rc_txt = "OK" if rc == 0 else "FAIL"
            dur = entry.get("duration", 0.0)
            cached = " (cached)" if entry.get("cached") else ""
            last = entry.get("last", "")
            print(f"- {entry.get('project', '?')}: {rc_txt} {dur:.1f}s{cached} {last}")
