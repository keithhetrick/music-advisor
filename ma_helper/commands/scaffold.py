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
    print("[ma] scaffold smoke is deprecated; use `ma smoke <audio>`")
    return 0
