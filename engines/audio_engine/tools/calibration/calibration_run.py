#!/usr/bin/env python3
"""
Run the Automator over a calibration tree so that each anchor writes packs under <anchor>/_packs.

Usage:
  python calibration_run.py --root "/.../audio_norm"
  # Optional env respected by automator.sh: REGION, PROFILE, BASELINE_PATH, AUTO_USE_NORM, etc.
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
from security import subprocess as sec_subprocess
from security.config import CONFIG as SEC_CONFIG

def run(cmd, env=None):
    sec_subprocess.run_safe(
        cmd,
        allow_roots=SEC_CONFIG.allowed_binary_roots,
        timeout=SEC_CONFIG.subprocess_timeout,
        check=True,
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Folder containing anchor subfolders (e.g., .../audio_norm)")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"[calibration_run] not a dir: {root}", file=sys.stderr)
        sys.exit(2)

    # tools/automator_batch.sh already does exactly what we want. Prefer it if present.
    batch = (Path(__file__).parents[1] / "automator_batch.sh")
    if batch.exists():
        run(["bash", str(batch), str(root)])
        return

    # Fallback inline (just in case)
    automator = (Path(__file__).parents[1].parent / "automator.sh")
    if not automator.exists():
        print("[calibration_run] automator.sh not found next to repo root.", file=sys.stderr)
        sys.exit(2)

    for anchor_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
        anchor = anchor_dir.name
        print(f"=== Automating anchor: {anchor} ===")
        os.environ["ARCHIVE_ROOT"] = str(anchor_dir / "_packs")
        os.environ["LOG_ROOT"] = str(anchor_dir / "_logs")
        (anchor_dir / "_packs").mkdir(parents=True, exist_ok=True)
        (anchor_dir / "_logs").mkdir(parents=True, exist_ok=True)
        for wav in sorted(anchor_dir.rglob("*.wav")):
            print(f"[auto] {anchor} :: {wav.name}")
            run([str(automator), str(wav)])

    print("✓ calibration_run complete.")

if __name__ == "__main__":
    main()
