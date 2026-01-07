#!/usr/bin/env python3
"""
Offline generator for repo surgery reports.

Outputs under docs/repo_surgery/.
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = REPO_ROOT / "docs" / "repo_surgery"
RAW_ROOT = DOC_ROOT / "raw"

EXCLUDE_GLOBS = [
    "!archive/**",
    "!docs/repo_surgery/**",
    "!docs/repo_surgery/*",
    "!archive/quarantine/**",
    "!.venv/**",
    "!.pytest_cache/**",
    "!dist/**",
    "!build/**",
]

ACTIVE_ROOTS = ["engines", "shared", "hosts", "ma_helper", "tools", "infra", "tests", "scripts", "src"]
GLOB_EXCLUDES = [item for g in EXCLUDE_GLOBS for item in ("--glob", g)]


# --------------------------- helpers --------------------------- #
def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def ensure_dirs() -> None:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    DOC_ROOT.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def gather_baseline() -> Dict[str, str]:
    cmds = [
        ["python", "--version"],
        ["git", "status", "-sb"],
        ["git", "rev-parse", "HEAD"],
        ["rg", "--version"],
        ["ls", "-la"],
    ]
    lines: List[str] = []
    results: Dict[str, str] = {}
    for cmd in cmds:
        rc, out, err = run_cmd(cmd)
        key = " ".join(cmd)
        results[key] = out.strip() or err.strip()
        lines.append(f"$ {' '.join(cmd)}\n{out or err}")
    write_text(RAW_ROOT / "baseline.txt", "\n\n".join(lines).strip() + "\n")

    rc, out, _ = run_cmd(["git", "ls-files"])
    if rc == 0:
        write_text(RAW_ROOT / "git_ls_files.txt", out)
    return results


# --------------------------- entrypoints --------------------------- #
def scan_entrypoints() -> Tuple[List[Dict], List[str]]:
    entrypoints: List[Dict] = []
    doc_cmds: List[str] = []

    # A) find shell/python files
    shell_py_files: List[Path] = []
    for root in ["infra", "tools", "scripts"]:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for path in root_path.rglob("*"):
            if path.is_file() and path.suffix in {".sh", ".py"}:
                if len(path.relative_to(root_path).parts) <= 4:
                    shell_py_files.append(path)

    # B) Python main / CLI hits via rg
    py_main_hits = run_cmd(["rg", "-n", "if __name__ == .__main__.", "-S", "."] + GLOB_EXCLUDES)[1].splitlines()
    py_cli_hits = run_cmd(
        [
            "rg",
            "-n",
            r"\b(argparse\.ArgumentParser|click\.|typer\.|fire\.Fire|uvicorn\.run)\b",
            "-S",
            ".",
        ]
        + GLOB_EXCLUDES
    )[1].splitlines()
    py_hit_paths = {Path(line.split(":", 1)[0]) for line in py_main_hits + py_cli_hits if ":" in line}

    # C) Makefile/Taskfile existence
    makefile = REPO_ROOT / "Makefile"
    taskfiles = [REPO_ROOT / "Taskfile.yml", REPO_ROOT / "Taskfile.yaml"]

    # Doc commands
    doc_hits = run_cmd(
        [
            "rg",
            "-n",
            r"^(\$|```bash|```sh)|make |python |./infra/scripts|ma_orchestrator|ma_helper",
            "-S",
            "README*",
            "docs",
        ]
    )[1].splitlines()
    seen_cmds = set()
    for line in doc_hits:
        cmd_part = line.split(":", 2)[-1].strip()
        if cmd_part and cmd_part not in seen_cmds:
            seen_cmds.add(cmd_part)
            doc_cmds.append(cmd_part)
            if len(doc_cmds) >= 30:
                break

    # Parse Make targets
    make_targets: List[Dict] = []
    if makefile.exists():
        targets: Dict[str, List[str]] = {}
        current: Optional[str] = None
        for line in makefile.read_text().splitlines():
            if line.startswith("#") or line.strip().startswith(".PHONY"):
                continue
            m = re.match(r"^([A-Za-z0-9_.-]+):", line)
            if m:
                current = m.group(1)
                targets[current] = []
            elif current and line.startswith("\t"):
                targets[current].append(line.strip())
        for name, recipe in targets.items():
            entrypoints.append(
                {
                    "path": "Makefile",
                    "kind": "make",
                    "name": name,
                    "calls": [r for r in recipe],
                    "used_by": [],
                }
            )
            make_targets.append({"name": name, "calls": recipe})

    # Parse Taskfile
    for tf in taskfiles:
        if not tf.exists():
            continue
        tasks: Dict[str, List[str]] = {}
        cur: Optional[str] = None
        for line in tf.read_text().splitlines():
            if re.match(r"^\s*[A-Za-z0-9_.-]+:\s*$", line) and not line.startswith(" "):
                cur = line.strip().rstrip(":")
                tasks[cur] = []
            elif cur and line.strip().startswith("-"):
                tasks[cur].append(line.strip("- ").strip())
        for name, cmds in tasks.items():
            entrypoints.append(
                {
                    "path": tf.relative_to(REPO_ROOT).as_posix(),
                    "kind": "task",
                    "name": name,
                    "calls": cmds,
                    "used_by": [],
                }
            )

    def extract_calls_from_shell(text: str) -> List[str]:
        calls = []
        for pat in [
            r"python [^\n;]+",
            r"bash [^\n;]+",
            r"zsh [^\n;]+",
            r"make [^\n;]+",
        ]:
            calls.extend(re.findall(pat, text))
        return list(dict.fromkeys(calls))

    # Entry for shell/python files
    for path in sorted(shell_py_files):
        rel = path.relative_to(REPO_ROOT).as_posix()
        kind = "shell" if path.suffix == ".sh" else "python"
        calls = extract_calls_from_shell(path.read_text(errors="ignore"))
        used_by = [h for h in doc_cmds if rel in h]
        entrypoints.append(
            {
                "path": rel,
                "kind": kind,
                "name": Path(rel).name,
                "calls": calls,
                "used_by": used_by,
                "main_hit": str(path) in {str(p) for p in py_hit_paths},
            }
        )

    # Doc canonical commands list included as entrypoints
    for cmd in doc_cmds:
        entrypoints.append(
            {"path": "docs", "kind": "doc_command", "name": cmd[:60], "calls": [], "used_by": []}
        )

    # Save raw JSON
    write_text(RAW_ROOT / "entrypoints.json", json.dumps(entrypoints, indent=2))

    # Human-readable markdown
    rows = ["| Path | Kind | Calls | Used by |", "| --- | --- | --- | --- |"]
    for ep in entrypoints:
        calls_str = "<br>".join(ep.get("calls", [])[:5])
        used_by_str = "<br>".join(ep.get("used_by", [])[:3])
        rows.append(f"| {ep.get('path')} | {ep.get('kind')} | {calls_str} | {used_by_str} |")
    doc_cmd_section = "\n".join(f"- {cmd}" for cmd in doc_cmds)
    write_text(
        DOC_ROOT / "entrypoints.md",
        "\n".join(
            [
                "# Entrypoints",
                "",
                "## Inventory",
                "\n".join(rows),
                "",
                "## Doc-canonical commands (top 30)",
                doc_cmd_section or "_none_",
            ]
        )
        + "\n",
    )

    return entrypoints, doc_cmds


# --------------------------- boundary violations --------------------------- #
def collect_boundary_violations() -> List[Dict]:
    violations: List[Dict] = []

    def parse_rg(output: str, violation_type: str) -> None:
        for line in output.splitlines():
            if ":" not in line:
                continue
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            path, lineno, snippet = parts[0], parts[1], parts[2].strip()
            layer = path.split("/", 1)[0]
            violations.append(
                {
                    "layer": layer,
                    "violation_type": violation_type,
                    "file": path,
                    "line": lineno,
                    "snippet": snippet,
                }
            )

    cmds = [
        ("engine_imports_tools", ["rg", "-n", "^(from|import) tools(\\.|$)", "-g", "*.py", "engines/**/src", "-S", *GLOB_EXCLUDES]),
        ("shared_imports_tools", ["rg", "-n", "^(from|import) tools(\\.|$)", "-g", "*.py", "shared", "-S", *GLOB_EXCLUDES]),
        ("engine_imports_hosts", ["rg", "-n", "^(from|import) hosts(\\.|$)", "-g", "*.py", "engines/**/src", "-S", *GLOB_EXCLUDES]),
        (
            "sys_path_mutation",
            [
                "rg",
                "-n",
                "sys\\.path\\.(insert|append)|PYTHONPATH=",
                "-g",
                "*.py",
                "engines",
                "shared",
                "hosts",
                "tools",
                "infra",
                "tests",
                "ma_helper",
                "src",
            ]
            + GLOB_EXCLUDES,
        ),
        ("wildcard_reexport", ["rg", "-n", "from .* import \\*|import \\*", "-g", "*.py", "engines/**/src", "shared", "hosts", "-S", *GLOB_EXCLUDES]),
    ]
    for vtype, cmd in cmds:
        rc, out, _ = run_cmd(cmd)
        if rc == 0 or out:
            parse_rg(out, vtype)

    # Write CSV
    csv_path = RAW_ROOT / "boundary_violations.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["layer", "violation_type", "file", "line", "snippet"])
        writer.writeheader()
        writer.writerows(violations)

    # Human-readable grouped
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for v in violations:
        grouped[v["violation_type"]].append(v)
    lines: List[str] = ["# Boundary Violations", ""]
    for vtype, items in grouped.items():
        lines.append(f"## {vtype}")
        for v in items:
            lines.append(f"- {v['file']}:{v['line']} — {v['snippet']}")
        lines.append("")
    write_text(DOC_ROOT / "boundary_violations.md", "\n".join(lines))
    return violations


# --------------------------- prune candidates --------------------------- #
def collect_prune_candidates(entrypoints: List[Dict]) -> List[Dict]:
    entrypoint_paths = {ep.get("path") for ep in entrypoints}
    git_files = (RAW_ROOT / "git_ls_files.txt").read_text().splitlines()

    denylist = {
        "archive/builder_pack/builder/export/MusicAdvisor/requirements.txt",
        "archive/builder_pack/builder/export/MusicAdvisor/README.md",
        "archive/builder_pack/builder/export/MusicAdvisor/README_HF_A12.md",
    }

    def ref_counts(path: str) -> Tuple[int, int, List[str]]:
        # active refs exclude repo_surgery outputs/quarantine and limit to active roots
        cmd = ["rg", "-n", Path(path).name, *ACTIVE_ROOTS, *GLOB_EXCLUDES]
        rc, out, _ = run_cmd(cmd)
        active_hits = out.splitlines() if out else []

        # doc refs (docs/**/*.md only)
        rc2, out2, _ = run_cmd(["rg", "-n", Path(path).name, "docs", "-g", "*.md"] + GLOB_EXCLUDES)
        doc_hits = out2.splitlines() if out2 else []

        return len(active_hits), len(doc_hits), (active_hits[:2] + doc_hits[:1])

    candidates: List[Dict] = []
    for path in git_files:
        if not path or path.startswith(".git"):
            continue
        confidence = None
        category = None
        rationale_parts = []
        active_refs, doc_refs, ref_samples = ref_counts(path)
        if path.startswith("archive/"):
            category = "archive"
            if path in denylist:
                confidence = "LOW"
            else:
                confidence = "HIGH" if active_refs == 0 else "MED"
            rationale_parts.append("under archive/")
        elif path.startswith("tools/") and path not in entrypoint_paths:
            category = "tools_unreferenced"
            confidence = "HIGH" if active_refs == 0 else ("MED" if active_refs == 1 else "LOW")
            rationale_parts.append("tools file not in entrypoint inventory")
        elif re.search(r"(legacy|deprecated|old|_v1|_v0)", Path(path).name, re.I):
            category = "legacy_named"
            confidence = "HIGH" if active_refs == 0 else ("MED" if active_refs == 1 else "LOW")
            rationale_parts.append("legacy-named file")
        else:
            continue
        rationale_parts.append(f"active_refs={active_refs}")
        candidates.append(
            {
                "confidence": confidence or "LOW",
                "category": category or "misc",
                "path": path,
                "refs_count": active_refs,
                "active_refs_count": active_refs,
                "doc_refs_count": doc_refs,
                "referenced_by": "; ".join(ref_samples),
                "rationale": "; ".join(rationale_parts),
            }
        )

    # Write CSV
    with (RAW_ROOT / "prune_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "confidence",
                "category",
                "path",
                "refs_count",
                "active_refs_count",
                "doc_refs_count",
                "referenced_by",
                "rationale",
            ],
        )
        writer.writeheader()
        writer.writerows(candidates)

    # Markdown summary
    top = sorted(candidates, key=lambda c: (c["confidence"], -c["refs_count"]))[:50]
    lines = ["# Prune Candidates", ""]
    for c in top:
        lines.append(
            f"- [{c['confidence']}] {c['path']} ({c['category']}) "
            f"refs={c['refs_count']}; {c['rationale']}"
        )
    lines.append("")
    lines.append("## Quarantine Plan")
    lines.append("- Stage 0: move HIGH confidence into archive/quarantine/YYYYMMDD/, exclude from PYTHONPATH/tests.")
    lines.append("- Stage 1: after 2 clean runs, delete HIGH; keep MED for review.")
    lines.append("- Stage 2: merge duplicate tooling and collapse wrappers once coverage confirms.")
    write_text(DOC_ROOT / "prune_candidates.md", "\n".join(lines))
    return candidates


# --------------------------- report assembly --------------------------- #
def assemble_report(entrypoints: List[Dict], violations: List[Dict], prune_candidates: List[Dict]) -> None:
    ep_count = len([e for e in entrypoints if e.get("kind") != "doc_command"])
    viol_count = len(violations)
    high_prune = len([c for c in prune_candidates if c["confidence"] == "HIGH"])
    med_prune = len([c for c in prune_candidates if c["confidence"] == "MED"])

    # Boundary top 10
    top_viol = violations[:10]
    viol_lines = [f"- {v['violation_type']}: {v['file']}:{v['line']} — {v['snippet']}" for v in top_viol]

    report = [
        "# Repo Surgery Report",
        "",
        "## Executive Summary",
        f"- Entry points discovered: {ep_count}",
        f"- Boundary violations: {viol_count}",
        f"- Prune candidates: HIGH={high_prune}, MED={med_prune}",
        "- Top issues: duplicated tooling, engines/tools coupling, sys.path hacks, archive in-band, many wrappers.",
        "",
        "## Single Control Plane",
        "- Recommend: use `ma_orchestrator` + Makefile as the canonical runner. Deprecate ad-hoc shell shims; keep wrappers but forward to orchestrator.",
        "",
        "## Boundary Cleanup (top 10 receipts)",
        *viol_lines,
        "",
        "## Prune Plan",
        "- Stage 0: quarantine HIGH candidates (archive/* with no references).",
        "- Stage 1: delete HIGH after 2 clean runs; review MED in tools/ unreferenced.",
        "- Stage 2: merge duplicate wrappers (multiple *_v1 scripts).",
        "",
        "## Success Metrics",
        f"- Entry points reduced from {ep_count} -> target <= {max(1, ep_count//2)}.",
        f"- Boundary violations reduced from {viol_count} -> target <= {max(0, viol_count//2)}.",
        "- Smokes/tests runnable via single orchestrator entry.",
    ]
    write_text(DOC_ROOT / "REPORT.md", "\n".join(report) + "\n")


def main() -> None:
    ensure_dirs()
    gather_baseline()
    entrypoints, _ = scan_entrypoints()
    violations = collect_boundary_violations()
    prune_candidates = collect_prune_candidates(entrypoints)
    assemble_report(entrypoints, violations, prune_candidates)


if __name__ == "__main__":
    main()
