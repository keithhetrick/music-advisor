"""Textual TUI scaffold for ma_helper (split-pane)."""
from __future__ import annotations

import asyncio
from typing import List

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual import events
from textual.widgets import Static as RichStatic
from pathlib import Path
import json
from typing import List, Dict, Any
from rich.table import Table
from rich.console import Group
from asyncio import create_task
import time
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, ProgressColumn
from ma_helper.core.registry import load_registry
import re
import subprocess, sys, signal


class HelperTUI(App):
    CSS_PATH = None
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("/", "focus_search", "Search"),
        ("g", "show_graph", "Graph"),
        ("r", "rerun", "Rerun"),
        ("c", "cancel", "Cancel"),
        ("?", "help", "Help"),
    ]

    timeline_data: reactive[Dict[str, Any]] = reactive({})
    logs_data: reactive[str] = reactive("Logs: empty.")
    event_data: reactive[Dict[str, Any]] = reactive({})
    focus_task: reactive[str | None] = reactive(None)
    tab: reactive[str] = reactive("timeline")  # timeline|logs|graph
    filter_text: reactive[str] = reactive("")
    live_pids: reactive[Dict[str, int]] = reactive({})
    help_visible: reactive[bool] = reactive(False)
    focus_logs_for: reactive[str | None] = reactive(None)

    def __init__(self, projects: List[str], results_path: Path | None = None, log_path: Path | None = None, interval: float = 1.0, state_home: Path | None = None, **kwargs):
        super().__init__(**kwargs)
        self.projects = projects
        self.results_path = results_path
        self.log_path = log_path
        self.interval = interval
        # Backward compatibility
        if state_home is None:
            from ma_helper.core.env import STATE_HOME
            state_home = STATE_HOME
        self.state_home = state_home

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Horizontal(
            Tree("Projects", id="proj-tree"),
            Vertical(
                VerticalScroll(Static("Timeline coming soon", id="timeline"), id="timeline-pane"),
                VerticalScroll(Static("Logs coming soon", id="logs"), id="logs-pane"),
                Static("", id="help-overlay"),
                id="right-pane",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one("#proj-tree", Tree)
        for name in sorted(self.projects):
            tree.root.add(name)
        tree.root.expand()
        # initial fill
        self.refresh_timeline()
        self.refresh_logs()
        # periodic refresh
        self.set_interval(self.interval, self.refresh_timeline)
        self.set_interval(self.interval, self.refresh_logs)
        self.set_interval(self.interval, self.refresh_events)

    async def action_focus_search(self) -> None:
        # Simple input prompt in logs pane
        try:
            prompt = "Filter project (regex, blank to clear). Enter=apply, Esc=close"
            from textual.widgets import Input
            inp = Input(placeholder=prompt, id="filter-input")
            self.query_one("#logs-pane", VerticalScroll).mount(inp)
            await inp.focus()

            @inp.on_submitted
            def _on_submit(event):
                text = event.value.strip()
                self.filter_text = text
                inp.remove()

            @inp.on_blur
            def _on_blur(event):
                if inp.parent:
                    inp.remove()
        except Exception:
            self.query_one("#logs", Static).update("Filter input failed.")

    async def action_show_graph(self) -> None:
        try:
            reg = load_registry()
            lines = ["Graph (dep -> project):"]
            edges = []
            for name, meta in reg.items():
                for dep in meta.get("deps", []):
                    edges.append((dep, name))
            for dep, proj in sorted(edges):
                lines.append(f"{dep} -> {proj}")
            if not edges:
                lines.append("(no edges)")
            self.query_one("#timeline", Static).update("\n".join(lines))
        except Exception:
            self.query_one("#timeline", Static).update("Graph: unable to render.")

    async def action_rerun(self) -> None:
        try:
            import subprocess, sys
            # Use the ma console script directly to avoid missing kwargs
            subprocess.Popen(["ma", "rerun-last"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        except Exception:
            self.query_one("#logs", Static).update("rerun: unable to execute.")

    async def action_cancel(self) -> None:
        # Attempt to cancel the focused task if PID is known
        target = self.focus_task
        if not target and self.live_pids:
            # Cancel the first active pid if no focus
            target, _ = next(iter(self.live_pids.items()))
        if not target or target not in self.live_pids:
            self.query_one("#logs", Static).update("cancel: no active PID to cancel.")
            return
        pid = self.live_pids.get(target)
        try:
            os.kill(pid, signal.SIGTERM)
            self.query_one("#logs", Static).update(f"cancel: sent SIGTERM to {target} (pid {pid})")
        except Exception as exc:
            self.query_one("#logs", Static).update(f"cancel: failed to kill pid {pid} ({exc})")

    async def action_help(self) -> None:
        self.help_visible = not self.help_visible
        self.render_help()

    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        # When a project node is selected, focus logs for that project
        node = event.node
        label = str(node.label)
        self.focus_logs_for = label if label else None

    def refresh_timeline(self) -> None:
        if not self.results_path or not self.results_path.exists():
            self.timeline_data = {"label": "none", "rows": []}
            return
        try:
            data = json.loads(self.results_path.read_text())
            rows = data.get("results", [])
            label = data.get("label", "last run")
            self.timeline_data = {"label": label, "rows": rows}
        except Exception:
            self.timeline_data = {"label": "error", "rows": []}

    def refresh_logs(self) -> None:
        if not self.log_path or not self.log_path.exists():
            self.logs_data = "Logs: no log file yet."
            return
        try:
            lines = self.log_path.read_text().splitlines()[-200:]
            if self.focus_logs_for:
                filtered = [ln for ln in lines if self.focus_logs_for in ln]
                lines = filtered[-100:]
            self.logs_data = "\n".join(lines) if lines else "Logs: empty."
        except Exception:
            self.logs_data = "Logs: unable to read log file."

    def _update_pids(self, latest_events: Dict[str, Any]) -> None:
        # Track PIDs if present for cancel support
        pids = {}
        for ev in latest_events.values():
            pid = ev.get("pid")
            proj = ev.get("project")
            if proj and pid:
                pids[proj] = pid
        if pids:
            self.live_pids = pids

    def refresh_events(self) -> None:
        # Read latest events (if any) and merge into timeline
        event_path = self.state_home / "ui_events.ndjson"
        if not event_path.exists():
            return
        try:
            lines = event_path.read_text().splitlines()[-200:]
        except Exception:
            return
        latest = {}
        for line in lines:
            try:
                ev = json.loads(line)
            except Exception:
                continue
            proj = ev.get("project")
            if proj:
                latest[proj] = ev
        if latest:
            self.event_data = latest
            self._update_pids(latest)

    def watch_timeline_data(self, data: Dict[str, Any]) -> None:
        label = data.get("label", "last run")
        rows = data.get("rows", [])
        if not rows:
            self.query_one("#timeline", Static).update("Timeline: no results yet.")
            return
        table = Table(title=f"{label}", expand=True)
        table.add_column("project", style="bold")
        table.add_column("rc", justify="center")
        table.add_column("dur", justify="right")
        table.add_column("cached", justify="center")
        for row in rows:
            rc = row.get("rc")
            rc_txt = "✅" if rc == 0 else "❌"
            dur = row.get("duration", 0.0)
            cached = "hit" if row.get("cached") else ""
            table.add_row(row.get("project", "?"), rc_txt, f"{dur:.1f}s", cached)
        self.query_one("#timeline", Static).update(table)

    def watch_logs_data(self, data: str) -> None:
        self.query_one("#logs", Static).update(data)

    def watch_event_data(self, data: Dict[str, Any]) -> None:
        if not data:
            return
        spinners = ["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"]
        spin = spinners[int(time.time()) % len(spinners)]
        table = Table(title="Live run", expand=True)
        table.add_column("project", style="bold")
        table.add_column("status", justify="center")
        table.add_column("dur", justify="right")
        table.add_column("cache", justify="center")
        table.add_column("last", overflow="fold")
        for proj, ev in sorted(data.items()):
            rc = ev.get("rc")
            status = spin if rc is None else ("✅" if rc == 0 else "❌")
            dur = ev.get("duration", 0.0)
            cached = "hit" if ev.get("cached") else ""
            last = ev.get("last", "")
            if self.filter_text:
                try:
                    if not re.search(self.filter_text, proj):
                        continue
                except re.error:
                    pass
            style = "dim" if (self.focus_task and proj != self.focus_task) else None
            table.add_row(proj, status, f"{dur:.1f}s", cached, last, style=style)
        self.query_one("#timeline", Static).update(table)

    def render_help(self) -> None:
        if not self.help_visible:
            self.query_one("#help-overlay", Static).update("")
            return
        lines = [
            "Keys: q quit | / filter | g graph | r rerun-last | c cancel | ? help toggle",
            "Tree select: focuses log filter for that project",
            "Filter: regex on project names; Esc/blur to close input",
        ]
        self.query_one("#help-overlay", Static).update("\n".join(lines))
