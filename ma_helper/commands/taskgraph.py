"""Task graph runner with live TUI-lite (Nx/Turbo style foundation)."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Dict

import tomllib

from ma_helper.core.env import ROOT
import json
import tempfile

from ma_helper.core.tasks import (
    load_task_specs,
    topo_order,
    outputs_fresh,
    hash_inputs,
    pack_outputs,
    unpack_outputs,
    LocalCache,
    RemoteCache,
    S3Cache,
)
from ma_helper.commands.ux import render_error_panel, render_hint_panel


def _load_tasks(config_path: Path) -> Dict[str, object]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("rb") as fh:
        return tomllib.load(fh)


def _live_table(names):
    """Return (cb, finish) live table helpers using rich if available."""
    try:
        from rich.live import Live
        from rich.table import Table
        from rich.layout import Layout
        from rich.panel import Panel

        state = {name: {"rc": None, "duration": 0.0, "cached": False, "last": ""} for name in names}
        logs: list[str] = []

        def _table():
            tbl = Table(title="tasks run", expand=True)
            tbl.add_column("task")
            tbl.add_column("rc")
            tbl.add_column("duration")
            tbl.add_column("cached")
            tbl.add_column("last")
            for name, entry in state.items():
                rc = entry.get("rc")
                rc_txt = "-" if rc is None else ("✅" if rc == 0 else "❌")
                dur = entry.get("duration", 0.0)
                cached = "yes" if entry.get("cached") else ""
                last = entry.get("last", "")
                tbl.add_row(name, rc_txt, f"{dur:.1f}s", cached, last)
            return tbl

        def _layout():
            lay = Layout()
            lay.split_column(Layout(name="tasks"), Layout(name="logs", size=6))
            lay["tasks"].update(_table())
            log_text = "\n".join(logs[-5:]) if logs else "..."
            lay["logs"].update(Panel(log_text, title="recent logs", padding=(0, 1)))
            return lay

        live = Live(_layout(), refresh_per_second=4)
        live.start()

        def cb(entry):
            state[entry["task"]] = entry
            if entry.get("last"):
                logs.append(f"{entry['task']}: {entry['last']}")
            live.update(_layout())

        def finish():
            live.update(_layout())
            live.stop()

        return cb, finish
    except Exception:
        return None, lambda: None


def handle_tasks_run(args, run_cmd, log_event) -> int:
    cfg_path = Path(args.config or "ma_helper.toml")
    try:
        raw = _load_tasks(cfg_path)
    except Exception as exc:
        render_error_panel(f"Failed to read config {cfg_path}: {exc}")
        return 1
    specs = load_task_specs(raw, ROOT)
    if not specs:
        render_error_panel(
            f"No tasks found in {cfg_path}. Add [tasks.<name>] entries like:\n[tasks.build]\ncommand = \"make build\""
        )
        return 1
    if args.name not in specs:
        render_error_panel(f"Task '{args.name}' not found.", [f"Available: {', '.join(sorted(specs))}"])
        return 1
    try:
        ordered = topo_order(specs, args.name)
    except Exception as exc:
        render_error_panel(f"Task graph error: {exc}")
        return 1

    cache_mode = "remote" if args.remote_cache else ("local" if args.cache else "off")
    cache_backend = None
    manifest_dir = ROOT / ".ma_task_cache" / "manifests"
    tar_dir = ROOT / ".ma_task_cache" / "tarballs"
    if cache_mode == "local":
        cache_backend = LocalCache(ROOT / ".ma_task_cache")
    elif cache_mode == "remote":
        endpoint = args.remote_cache or os.environ.get("MA_TASK_CACHE_URL")
        if endpoint:
            if endpoint.startswith("s3://"):
                cache_backend = S3Cache(endpoint, ROOT)
            else:
                cache_backend = RemoteCache(endpoint, ROOT)

    live_cb, finish = _live_table([t.name for t in ordered])
    rc_overall = 0
    summary_rows = []
    try:
        for task in ordered:
            start = time.time()
            # cache check
            cache_hit = False
            cache_key = hash_inputs(task)
            if cache_mode != "off" and task.outputs:
                if outputs_fresh(task):
                    cache_hit = True
                elif cache_backend:
                    tar_dir.mkdir(parents=True, exist_ok=True)
                    tar_path = tar_dir / f"{task.name}-{cache_key}.tar.gz"
                    if cache_backend.fetch(cache_key, tar_path):
                        if unpack_outputs(tar_path, ROOT) and outputs_fresh(task):
                            cache_hit = True
            if cache_hit:
                entry = {"task": task.name, "rc": 0, "duration": 0.0, "cached": True, "last": "cache hit"}
                summary_rows.append(entry)
                if live_cb:
                    live_cb(entry)
                if log_event:
                    try:
                        log_event({"cmd": f"task {task.name}", "rc": 0, "duration_sec": 0.0, "cache": "hit", "cache_key": cache_key})
                    except Exception:
                        pass
                continue
            cmd_str = task.command
            print(f"[task] {task.name}: {cmd_str}")
            proc = subprocess.run(cmd_str, shell=True, cwd=ROOT, capture_output=True, text=True)
            rc = proc.returncode
            dur = time.time() - start
            last_line = (proc.stdout.splitlines() or [""])[-1] if proc.stdout else ""
            entry = {"task": task.name, "rc": rc, "duration": dur, "cached": False, "last": last_line[:60]}
            summary_rows.append(entry)
            if live_cb:
                live_cb(entry)
            if rc != 0:
                if proc.stdout:
                    print(proc.stdout.strip())
                if proc.stderr:
                    print(proc.stderr.strip())
            if log_event:
                try:
                    log_event({"cmd": f"task {task.name}", "rc": rc, "duration_sec": round(dur, 3), "cache": "miss", "cache_key": cache_key})
                except Exception:
                    pass
            if cache_backend and rc == 0:
                try:
                    tar_dir.mkdir(parents=True, exist_ok=True)
                    manifest_dir.mkdir(parents=True, exist_ok=True)
                    tar_path = pack_outputs(task, cache_key, ROOT)
                    manifest_path = manifest_dir / f"{task.name}-{cache_key}.json"
                    manifest_data = {"task": task.name, "cache_key": cache_key, "outputs": [str(o.path) for o in task.outputs]}
                    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
                    if tar_path:
                        cache_backend.store(cache_key, tar_path)
                    cache_backend.store(cache_key, manifest_path)
                except Exception:
                    pass
            if rc != 0 and not args.keep_going:
                rc_overall = rc
                break
        else:
            rc_overall = 0
    finally:
        finish()

    if args.json:
        import json

        print(json.dumps({"tasks": summary_rows, "rc": rc_overall}, indent=2))
    if args.html:
        try:
            from yattag import Doc
        except Exception:
            Doc = None
        if Doc is None:
            render_error_panel("HTML export requested but yattag not installed; pip install yattag", None)
        else:
            doc, tag, text = Doc().tagtext()
            with tag("html"):
                with tag("head"):
                    with tag("style"):
                        text("body{font-family:Arial;} table{border-collapse:collapse;} td,th{border:1px solid #ccc;padding:4px;} th{background:#f2f2f2;}")
                with tag("body"):
                    with tag("h3"):
                        text("ma_helper tasks-run summary")
                    with tag("p"):
                        text(f"rc={rc_overall}")
                    with tag("table"):
                        with tag("tr"):
                            for h in ["task", "rc", "duration", "cached", "last"]:
                                with tag("th"):
                                    text(h)
                        for row in summary_rows:
                            with tag("tr"):
                                with tag("td"):
                                    text(row["task"])
                                with tag("td"):
                                    text(str(row["rc"]))
                                with tag("td"):
                                    text(f"{row['duration']:.2f}s")
                                with tag("td"):
                                    text("yes" if row.get("cached") else "")
                                with tag("td"):
                                    text(row.get("last", ""))
            Path(args.html).write_text(doc.getvalue(), encoding="utf-8")
            print(f"[ma] wrote HTML summary to {args.html}")
    if rc_overall != 0:
        render_error_panel("Task run failed.", ["Re-run with --keep-going to continue deps", "Check command output above"])
    else:
        render_hint_panel("Tasks complete", ["Add outputs/inputs to enable cache", "Try --cache to skip fresh outputs"])
    return rc_overall
