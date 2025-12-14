"""Help/welcome/quickstart/palette/tour commands."""
from __future__ import annotations

from ma_helper.commands.ux import show_world


def handle_palette(hint_fn) -> int:
    show_world("palette")
    try:
        from ma_helper.ui_world import hint
    except Exception:
        hint = lambda msg: None  # type: ignore
    print("You are in the Music Advisor helper. Common commands:")
    palette = {
        "list": "list projects",
        "tasks": "common aliases",
        "test": "test <project> [--cache off|local|restore-only]",
        "test-all": "test-all [--parallel N] [--cache ...] [--require-preflight]",
        "affected": "affected --base origin/main [--require-preflight]",
        "run": "run <project>[:run|test]",
        "watch": "watch <project> [--hotkeys] [--require-preflight]",
        "verify": "verify [--require-preflight]",
        "preflight": "check registry paths",
        "dashboard": "dashboard --live|--json|--html",
        "tui": "tui --interval 1 --duration 60",
        "guard": "guard --set strict",
        "doctor": "doctor [--require-optional]",
        "ci-plan": "ci-plan --base origin/main --targets test run",
    }
    for k, v in palette.items():
        print(f"- {k}: {v}")
    print("\nGit helpers:")
    git_palette = {
        "git-status": "branch/dirty/ahead-behind (+ --branches to list recent)",
        "git-branch": "create feature branch with prefix",
        "git-upstream": "set upstream on current branch",
        "git-rebase": "rebase onto target (default origin/main)",
        "git-pull-check": "pull only if clean tree",
        "github-check": "pre-push/pre-CI gate (clean/upstream/preflight/verify)",
        "sparse": "git sparse-checkout helpers",
    }
    for k, v in git_palette.items():
        print(f"- {k}: {v}")
    hint("Next: ma list | ma affected --base origin/main | ma dashboard --json")
    return 0


def handle_quickstart(hint_fn) -> int:
    show_world("quickstart")
    try:
        from ma_helper.ui_world import hint
    except Exception:
        hint = lambda msg: None  # type: ignore
    print("Start here:")
    steps = [
        "ma list            # see all projects",
        "ma select          # interactive picker for test/run/deps",
        "ma affected --base origin/main   # run tests for changed projects",
        "ma dashboard --live             # live monorepo dashboard",
        "ma verify                       # lint+type+smoke+affected",
        "ma guard --set strict           # opt into confirmations",
    ]
    for s in steps:
        print(f"- {s}")
    hint("Next: ma palette | ma doctor | ma ci-plan --matrix")
    return 0
