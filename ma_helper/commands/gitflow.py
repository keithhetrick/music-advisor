"""Git hook/precommit helpers."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ma_helper.core.config import RuntimeConfig


def handle_hook(args, runtime: RuntimeConfig = None) -> int:
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root
    if args.name == "pre-push":
        hook_path = root / ".git" / "hooks" / "pre-push"
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


def handle_precommit(args, runtime: RuntimeConfig = None) -> int:
    if runtime is None:
        from ma_helper.core.env import ROOT
        root = ROOT
    else:
        root = runtime.root
    hook_path = root / ".git" / "hooks" / "pre-commit"
    content = "#!/bin/sh\npython -m ma_helper lint\n"
    if args.action == "install":
        hook_path.write_text(content)
        hook_path.chmod(0o755)
        print(f"[ma] wrote hook to {hook_path}")
    elif args.action == "uninstall":
        if hook_path.exists():
            hook_path.unlink()
            print(f"[ma] removed hook from {hook_path}")
        else:
            print("[ma] hook not installed")
    else:
        print(content)
    return 0
