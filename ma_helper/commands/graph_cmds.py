"""Graph commands (ANSI + mermaid/dot emitters)."""
from __future__ import annotations

from ma_helper.core.registry import load_registry


def graph_ansi(reg, flt: str | None) -> int:
    items = reg.items()
    if flt:
        items = [(k, v) for k, v in items if flt in k or flt in v.get("path", "")]
    print("Project graph (deps):")
    for name, meta in items:
        deps = ", ".join(meta.get("deps", [])) or "none"
        print(f"- {name}: {deps}")
    return 0


def graph_mermaid(reg, flt: str | None) -> int:
    items = reg.items()
    if flt:
        items = [(k, v) for k, v in items if flt in k or flt in v.get("path", "")]
    print("graph TD")
    for name, meta in items:
        for dep in meta.get("deps", []):
            print(f"  {dep} --> {name}")
    return 0


def handle_graph(fmt: str, flt: str | None) -> int:
    reg = load_registry()
    if fmt == "ansi":
        return graph_ansi(reg, flt)
    if fmt == "mermaid":
        return graph_mermaid(reg, flt)
    if fmt == "dot":
        for name, meta in reg.items():
            if flt and flt not in name and flt not in meta.get("path", ""):
                continue
            for dep in meta.get("deps", []):
                print(f"\"{dep}\" -> \"{name}\";")
        return 0
    print(f"[ma] unknown graph format: {fmt}")
    return 1
