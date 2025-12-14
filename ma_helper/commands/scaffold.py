"""Scaffold and smoke helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ma_helper.core.env import ROOT


def handle_scaffold(args) -> int:
    dest = Path(args.path) if args.path else (ROOT / "tools" / "scaffolds" / args.name)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "README.md").write_text(f"# {args.name}\n\nType: {args.type}\n")
    print(f"[ma] scaffolded {args.type} at {dest}")
    if args.write_registry:
        print("[ma] registry update not automated here; use ma registry add.")
    return 0


def handle_smoke(target: str) -> int:
    if target == "pipeline":
        cmds = [
            "python tools/ma_orchestrator.py test-all",
            "python tools/ma_orchestrator.py run audio_engine",
        ]
    elif target == "full":
        cmds = ["python tools/ma_orchestrator.py test-all", "python tools/ma_orchestrator.py run advisor_host"]
    else:
        print("Smokes: pipeline | full")
        return 0
    for cmd in cmds:
        print(f"[ma] {cmd}")
        rc = subprocess.call(cmd, shell=True, cwd=ROOT)
        if rc != 0:
            return rc
    return 0
