"""Smoke and playbook helpers."""
from __future__ import annotations

import subprocess
from typing import Dict, List

from ma_helper.core.env import ROOT

SMOKE_CMDS: Dict[str, str] = {
    "pipeline": "./infra/scripts/quick_check.sh",
    "full": "./infra/scripts/e2e_app_smoke.sh",
}


def run_smoke(target: str) -> int:
    if target == "menu":
        print("Smokes:")
        for key, val in SMOKE_CMDS.items():
            print(f"- {key}: {val}")
        return 0
    cmd = SMOKE_CMDS.get(target)
    if not cmd:
        print(f"[ma] unknown smoke target {target}")
        return 1
    print(f"[ma] running smoke '{target}': {cmd}")
    return subprocess.call(cmd, shell=True, cwd=ROOT)
