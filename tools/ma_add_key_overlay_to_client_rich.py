#!/usr/bin/env python3
"""
Inject a KEY LANE OVERLAY (KEY) block into existing .client.rich.txt files.

Behavior:
- Looks for a sibling <audio_name>.key_norms.json in the same directory.
- Builds a compact overlay block (using ma_merge_client_and_hci formatting) and inserts it
  just before NEIGHBOR_META (or appends at the end if not found).
- Removes any existing KEY LANE OVERLAY block before inserting.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools import names  # noqa: E402
from tools.ma_merge_client_and_hci import _format_key_overlay  # noqa: E402


def _stem_from_client_rich(path: Path) -> str:
    suffix = names.client_rich_suffix()
    name = path.name
    if name.endswith(suffix):
        return name[: -len(suffix)]
    # Fallback: strip .rich.txt only
    if name.endswith(".rich.txt"):
        return name[: -len(".rich.txt")]
    return path.stem


def _drop_existing_key_overlay(lines: list[str]) -> list[str]:
    out: list[str] = []
    skipping = False
    for i, line in enumerate(lines):
        if "KEY LANE OVERLAY (KEY)" in line:
            skipping = True
            # drop preceding separator if present
            if out and out[-1].strip() == "# ====================================":
                out.pop()
            continue
        if skipping:
            if line.strip().startswith("# ===================================="):
                skipping = False
                out.append(line)
            continue
        out.append(line)
    return out


def inject_key_overlay(text: str, overlay: str) -> str:
    lines = text.splitlines()
    cleaned = _drop_existing_key_overlay(lines)
    overlay_lines = overlay.splitlines()

    # Insert before NEIGHBOR_META if present; else append.
    inserted = False
    new_lines: list[str] = []

    def _append_block(target: list[str], trailing_separator: bool = False) -> None:
        # Avoid double separators; only add if previous line is not already a separator.
        if target and target[-1].strip() == "# ====================================":
            target.extend(overlay_lines)
        else:
            target.extend(["# ===================================="] + overlay_lines)
        if trailing_separator:
            target.extend(["", "# ===================================="])

    for i, line in enumerate(cleaned):
        if not inserted and (line.strip().startswith("# NEIGHBOR_META") or line.strip().startswith("# ==== HISTORICAL")):
            # ensure we didn't already place separator immediately before
            if new_lines and new_lines[-1].strip() != "":
                new_lines.append("")
            _append_block(new_lines, trailing_separator=True)
            inserted = True
        new_lines.append(line)
    if not inserted:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        _append_block(new_lines)

    # Dedupe consecutive separators (ignore blank lines between).
    cleaned: list[str] = []
    last_nonblank: Optional[str] = None
    for line in new_lines:
        if line.strip():
            if line.strip() == "# ====================================" and last_nonblank == "# ====================================":
                continue
            cleaned.append(line)
            last_nonblank = line.strip()
        else:
            cleaned.append(line)

    # Collapse multiple blank lines
    collapsed: list[str] = []
    blank_streak = 0
    for line in cleaned:
        if line.strip():
            blank_streak = 0
            collapsed.append(line)
        else:
            blank_streak += 1
            if blank_streak <= 1:
                collapsed.append(line)

    # Drop a blank immediately after a separator if the next line is the KEY overlay header.
    final_lines: list[str] = []
    for idx, line in enumerate(collapsed):
        if (
            not line.strip()
            and idx > 0
            and collapsed[idx - 1].strip() == "# ===================================="
            and idx + 1 < len(collapsed)
            and collapsed[idx + 1].strip().startswith("# KEY LANE OVERLAY")
        ):
            continue
        final_lines.append(line)

    return "\n".join(final_lines) + ("\n" if not text.endswith("\n") else "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject KEY LANE OVERLAY block into .client.rich.txt using sibling key_norms sidecar.")
    ap.add_argument("--client-rich", required=True, help="Path to <audio>.client.rich.txt")
    ap.add_argument("--prefer-flat", action="store_true", help="Display flats when possible (enharmonic mapping).")
    ap.add_argument("--overlay-display-style", choices=["sharp", "flat", "auto"], default="auto", help="Preferred key spelling for overlay output.")
    args = ap.parse_args()
    client_path = Path(args.client_rich).expanduser().resolve()
    if not client_path.exists():
        raise SystemExit(f"client rich not found: {client_path}")

    audio_stem = _stem_from_client_rich(client_path)
    sidecar_path = client_path.parent / f"{audio_stem}{names.key_norms_sidecar_suffix()}"
    if not sidecar_path.exists():
        print(f"[key_overlay] skip: sidecar missing ({sidecar_path})")
        return 0

    try:
        payload = json.loads(sidecar_path.read_text())
    except Exception as exc:  # noqa: BLE001
        print(f"[key_overlay] skip: failed to read sidecar ({exc})")
        return 0
    if not isinstance(payload, dict) or not payload.get("lane_id") or not payload.get("song_key"):
        print("[key_overlay] skip: invalid payload structure")
        return 0

    overlay = _format_key_overlay(payload)
    if not overlay:
        print("[key_overlay] skip: invalid payload")
        return 0

    current = client_path.read_text()
    updated = inject_key_overlay(current, overlay)
    if updated != current:
        client_path.write_text(updated)
        print(f"[key_overlay] injected into {client_path}")
    else:
        print("[key_overlay] no changes (already present?)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
