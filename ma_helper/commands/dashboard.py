"""Dashboard/TUI helpers for CLI dispatch."""
from __future__ import annotations

from ma_helper.commands.visual import render_dashboard


def run_dashboard(as_json: bool, as_html: bool, live: bool, interval: float, duration: float) -> int:
    return render_dashboard(
        as_json=as_json,
        as_html=as_html,
        live=live,
        interval=interval,
        duration=duration,
    )
