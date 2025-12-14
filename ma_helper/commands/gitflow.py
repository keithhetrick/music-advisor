"""Git hook/precommit helpers."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ma_helper.core.env import ROOT


def handle_hook(args) -> int:
    if args.name == "pre-push":
        hook_path = ROOT / ".git" / "hooks" / "pre-push"
        content = "#!/bin/sh\npython -m ma_helper github-check --require-clean --preflight --verify\n"
        if args.install:
            hook_path.write_text(content)
            hook_path.chmod(0o755)
            print(f"[ma] wrote hook to {hook_path}")
        else:
            print(content)
        return 0
    print(f"[ma] unknown hook {args.name}")
    return 1


def handle_precommit(args) -> int:
    hook_path = ROOT / ".git" / "hooks" / "pre-commit"
    content = "#!/bin/sh\npython -m ma_helper lint\n"
    if args.action == "install":
        hook_path.write_text(content)
        hook_path.chmod(0o755)
        print(f"[ma] installed pre-commit hook at {hook_path}")
        return 0
    print(content)
    return 0
