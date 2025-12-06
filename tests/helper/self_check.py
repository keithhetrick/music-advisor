#!/usr/bin/env python3
"""
Lightweight self-checks for ma_helper (no pytest dependencies).
Run with: python tests/helper/self_check.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
MA = [sys.executable, "-m", "ma_helper"]


def run(cmd):
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return res.returncode, res.stdout + res.stderr


def check_palette():
    rc, out = run(MA + ["palette"])
    assert rc == 0
    assert "list projects" in out


def check_list():
    rc, out = run(MA + ["list"])
    assert rc == 0
    assert "Projects" in out


def check_preflight():
    rc, _ = run(MA + ["preflight"])
    assert rc in (0, 1)


def check_ci_plan():
    rc, out = run(MA + ["ci-plan", "--no-diff"])
    assert rc == 0
    assert "affected" in out or "include" in out


def check_dashboard_json():
    rc, out = run(MA + ["dashboard", "--json"])
    assert rc == 0
    assert "types" in out


def check_chat_dev():
    # tmux may not be available; ensure command returns successfully or prints guidance
    rc, out = run(MA + ["chat-dev"])
    assert rc in (0, 1)
    # We expect either tmux launch message or printed commands
    assert "chat" in out.lower() or "tmux" in out.lower()


def check_git_simulation():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "file.txt").write_text("hi")
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        # clean status
        res = subprocess.run(["git", "status", "--porcelain"], cwd=tmp_path, capture_output=True, text=True, check=True)
        assert res.stdout.strip() == "?? file.txt"  # untracked counts as dirty
        # ci-plan should fallback to all (no tests but should not crash)
        rc, _ = run(MA + ["ci-plan", "--no-diff"],)
        assert rc == 0


def check_state_relocation():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["MA_HELPER_HOME"] = tmp
        rc, _ = subprocess.run(MA + ["palette"], cwd=ROOT, env=env, capture_output=True, text=True).returncode, ""
        assert rc == 0


def check_quickstart():
    rc, out = run(MA + ["quickstart"])
    assert rc == 0
    assert "ma list" in out


def check_github_check_missing_git():
    # in a temp dir without .git
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # run in tmp by overriding cwd
        res = subprocess.run(MA + ["github-check", "--require-clean"], cwd=tmp, capture_output=True, text=True)
        assert res.returncode != 0


def main():
    checks = [
        ("palette", check_palette),
        ("list", check_list),
        ("preflight", check_preflight),
        ("ci-plan", check_ci_plan),
        ("github-check-missing-git", check_github_check_missing_git),
        ("dashboard-json", check_dashboard_json),
        ("chat-dev", check_chat_dev),
        ("git-simulation", check_git_simulation),
        ("state-relocation", check_state_relocation),
        ("quickstart", check_quickstart),
    ]
    failures = []
    for name, fn in checks:
        try:
            fn()
            print(f"[ok] {name}")
        except Exception as exc:
            print(f"[fail] {name}: {exc}")
            failures.append(name)
    if failures:
        sys.exit(1)
    print("[ma] helper self-checks passed")


if __name__ == "__main__":
    main()
