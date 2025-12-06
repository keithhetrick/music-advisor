#!/usr/bin/env python3
from __future__ import annotations

"""
hci_migrate_audio_axes_list_to_dict.py

One-time migration tool to convert legacy list-style audio_axes into
the new dict-style audio_axes for existing *.hci.json files.

Legacy shape (what some older HCI runs used):

  "audio_axes": [TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence]

New shape expected by v2 tools:

  "audio_axes": {
    "TempoFit": 0.xxx,
    "RuntimeFit": 0.xxx,
    "LoudnessFit": 0.xxx,
    "Energy": 0.xxx,
    "Danceability": 0.xxx,
    "Valence": 0.xxx
  }

We DO NOT change any scores (HCI_v1_score_raw, HCI_v1_score, etc.).
We just reshape the axes so v2 code can use them.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

AXIS_NAMES = [
    "TempoFit",
    "RuntimeFit",
    "LoudnessFit",
    "Energy",
    "Danceability",
    "Valence",
]


def _iter_hci_files(root: Path):
    """
    Recursively yield *.hci.json files under root.
    """
    for p in root.rglob("*.hci.json"):
        if p.is_file():
            yield p


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)
        f.write("\n")


def _migrate_axes(axes_value: Any, path: Path) -> Dict[str, float] | None:
    """
    If axes_value is a 6-element list, convert it to a dict using AXIS_NAMES.
    If it's already a dict, return None (no change).
    Otherwise, return None and let the caller decide how to handle.
    """
    # Already the correct shape
    if isinstance(axes_value, dict):
        return None

    # Legacy list shape
    if isinstance(axes_value, list):
        if len(axes_value) != len(AXIS_NAMES):
            print(
                f"[WARN] {path} has audio_axes list of length {len(axes_value)}, "
                f"expected {len(AXIS_NAMES)}; skipping."
            )
            return None

        mapping: Dict[str, float] = {}
        for name, val in zip(AXIS_NAMES, axes_value):
            try:
                mapping[name] = float(val)
            except Exception:
                mapping[name] = 0.0

        return mapping

    # Unknown shape
    print(f"[WARN] {path} has audio_axes of unsupported type {type(axes_value)}; skipping.")
    return None


def cmd_migrate(root: Path) -> None:
    """
    Run migration over all *.hci.json files under root.
    """
    hci_files = list(_iter_hci_files(root))
    if not hci_files:
        print(f"[WARN] No *.hci.json files found under {root}")
        return

    print(f"[INFO] Migrating audio_axes list->dict for {len(hci_files)} file(s) under {root}")

    updated = 0
    skipped = 0
    already_ok = 0

    for path in hci_files:
        try:
            hci = _load_json(path)
        except Exception as e:
            print(f"[WARN] Failed to read {path}: {e}")
            skipped += 1
            continue

        axes_value = hci.get("audio_axes")
        if axes_value is None:
            print(f"[WARN] {path} has no audio_axes; skipping.")
            skipped += 1
            continue

        migrated = _migrate_axes(axes_value, path)
        if migrated is None:
            # Either already dict or unsupported shape
            if isinstance(axes_value, dict):
                already_ok += 1
            else:
                skipped += 1
            continue

        # Update audio_axes in-place
        hci["audio_axes"] = migrated

        # Annotate meta so we know this file was migrated
        meta = hci.get("meta") or {}
        migration = meta.get("audio_axes_migration") or {}
        migration["migrated_by"] = "hci_migrate_audio_axes_list_to_dict_v1"
        migration["axis_names_order"] = AXIS_NAMES
        meta["audio_axes_migration"] = migration
        hci["meta"] = meta

        try:
            _dump_json(path, hci)
            updated += 1
        except Exception as e:
            print(f"[WARN] Failed to write {path}: {e}")
            skipped += 1

    print(
        f"[DONE] audio_axes migration under {root}: "
        f"updated={updated}, already_ok={already_ok}, skipped={skipped}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convert legacy list-style audio_axes to dict-style audio_axes in *.hci.json files."
    )
    ap.add_argument(
        "--root",
        required=True,
        help="Root directory to scan recursively for *.hci.json files.",
    )

    args = ap.parse_args()
    root = Path(args.root).resolve()
    cmd_migrate(root)


if __name__ == "__main__":
    main()
