"""Chat development helper (tmux layout or printed commands)."""
from __future__ import annotations

import shutil
import subprocess

from ma_helper.core.env import ROOT


def handle_chat_dev(args) -> int:
    chat_cmd = f"CHAT_ENDPOINT={args.endpoint} python tools/chat_cli.py"
    tail_cmd = f"tail -f {args.log_file}"
    helper_cmd = "python -m ma_helper shell"
    if shutil.which("tmux"):
        session = "chatdev"
        layout = (
            f"tmux new-session -d -s {session} '{chat_cmd}' \\; "
            f"split-window -h '{tail_cmd}' \\; "
            f"split-window -v '{helper_cmd}' \\; "
            "select-layout even-horizontal \\; "
            f"attach-session -t {session}"
        )
        print(f"[ma] launching tmux session '{session}' with chat/tail/shell panes")
        rc = subprocess.call(["bash", "-lc", layout], cwd=ROOT)
        if rc == 0:
            return rc
        print("[ma] tmux launch failed; falling back to manual commands.")
    else:
        print("[ma] tmux not found; run these in three terminals:")
        print(f"1) {chat_cmd}")
        print(f"2) {tail_cmd}")
        print(f"3) {helper_cmd}")
        return 0
    # fallback if tmux failed
    print("1) " + chat_cmd)
    print("2) " + tail_cmd)
    print("3) " + helper_cmd)
    return 0
