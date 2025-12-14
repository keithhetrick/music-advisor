"""Project registry and map helpers."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

from ma_helper.core.registry import filter_projects, load_registry
from ma_helper.core.env import ROOT


def handle_registry(args, registry_path=None) -> int:
    reg = load_registry(registry_path)
    action = args.reg_action
    if action == "list":
        for name in sorted(reg.keys()):
            print(name)
        return 0
    if action == "show":
        proj = reg.get(args.project)
        if not proj:
            print(f"[ma] project '{args.project}' not found")
            return 1
        print(json.dumps(proj, indent=2))
        return 0
    if action == "validate":
        ok = True
        for name, meta in reg.items():
            p = ROOT / meta.get("path", "")
            if not p.exists():
                ok = False
                print(f"[ma] missing path for {name}: {p}")
            for t in meta.get("tests", []):
                tp = ROOT / t
                if not tp.exists():
                    ok = False
                    print(f"[ma] missing test path for {name}: {tp}")
        return 0 if ok else 1
    if action == "lint":
        sorted_items = {k: reg[k] for k in sorted(reg.keys())}
        if args.fix:
            (ROOT / "project_map.json").write_text(json.dumps(sorted_items, indent=2) + "\n")
            print("[ma] project_map.json normalized.")
        else:
            print(json.dumps(sorted_items, indent=2))
        return 0
    if action == "add":
        name = args.name
        if name in reg:
            print(f"[ma] project {name} already exists; refusing to overwrite without explicit edit.")
            return 1
        entry = {
            "path": args.path,
            "tests": args.tests or [],
            "type": args.type,
        }
        if args.run:
            entry["run"] = args.run
        reg[name] = entry
        print("[ma] dry-run only" if not args.yes else "[ma] writing update")
        if args.yes:
            (ROOT / "project_map.json").write_text(json.dumps({k: reg[k] for k in sorted(reg.keys())}, indent=2) + "\n")
        else:
            print(json.dumps(entry, indent=2))
        return 0
    if action == "remove":
        name = args.name
        if name not in reg:
            print(f"[ma] project {name} not found")
            return 1
        print(f"[ma] removing {name}" + (" (dry-run)" if not args.yes else ""))
        if args.yes:
            reg.pop(name, None)
            (ROOT / "project_map.json").write_text(json.dumps({k: reg[k] for k in sorted(reg.keys())}, indent=2) + "\n")
        return 0
    return 1


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
            if subprocess.call(["which", "dot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                print("[ma] graphviz dot not found; install graphviz or use --graph dot/mermaid/text.")
                return 1
            proc = subprocess.run(["dot", "-Tsvg"], input="\n".join(dot_lines), text=True, capture_output=True)
            if proc.returncode != 0:
                print(proc.stderr)
                return proc.returncode
            svg_out = proc.stdout
            print(svg_out)
            if do_open and subprocess.call(["which", "open"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".svg")
                tmp.write(svg_out.encode("utf-8"))
                tmp.close()
                subprocess.call(["open", tmp.name])
            return 0
        if fmt == "html":
            html_body = "\n".join(dot_lines)
            print(f"<pre>{html_body}</pre>")
            return 0
    if fmt == "ansi":
        for name, meta in projects.items():
            print(f"{name}: {', '.join(meta.get('deps', [])) or 'none'}")
        return 0
    for name, meta in projects.items():
        deps = ", ".join(meta.get("deps", [])) or "none"
        print(f"{name}: {deps}")
    return 0
