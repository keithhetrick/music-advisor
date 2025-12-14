"""Richer live TUI helpers using Rich."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Any


@contextmanager
def live_split(status_fn: Callable[[], str], body_fn: Callable[[], str]):
    """Render a split-pane live view (status + body) if Rich is available; fallback no-op."""
    try:
        from rich.console import Console
        from rich.layout import Layout
        from rich.live import Live
        from rich.panel import Panel

        layout = Layout()
        layout.split_row(Layout(name="status", size=40), Layout(name="body"))
        layout["status"].update(Panel(status_fn(), title="Status", style="bold cyan", padding=(0, 1)))
        layout["body"].update(Panel(body_fn(), title="Output", style="dim", padding=(0, 1)))
        console = Console()
        live = Live(layout, refresh_per_second=4, console=console)
        live.start()

        def refresh():
            try:
                layout["status"].update(Panel(status_fn(), title="Status", style="bold cyan", padding=(0, 1)))
                layout["body"].update(Panel(body_fn(), title="Output", style="dim", padding=(0, 1)))
            except Exception:
                pass

        try:
            yield refresh
        finally:
            try:
                refresh()
            except Exception:
                pass
            live.stop()
    except Exception:
        yield lambda: None
