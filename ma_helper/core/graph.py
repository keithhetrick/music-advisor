"""Graph and topology helpers."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import sys
from typing import Dict, List


def topo_sort(projects, names: List[str]) -> List[str]:
    # Kahn's algorithm
    deps = {name: set(projects[name].deps) for name in names}
    incoming = {name: set() for name in names}
    for name in names:
        for dep in deps[name]:
            if dep in incoming:
                incoming[name].add(dep)
    sorted_list: List[str] = []
    while True:
        free = [n for n in names if n not in sorted_list and not incoming[n]]
        if not free:
            break
        free.sort()
        for n in free:
            sorted_list.append(n)
            for m in names:
                incoming[m].discard(n)
    return sorted_list


def emit_graph(projects, fmt: str) -> int:
    if fmt == "dot" or fmt == "svg":
        dot_lines = ["digraph G {"]
        dot_lines += [f'  "{dep}" -> "{name}"' for name, proj in projects.items() for dep in proj.deps] + ["}"]
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
