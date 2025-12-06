#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def load_hci(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_hci(path: Path, data: Dict[str, Any]) -> None:
    """
    Safely write updated JSON back to disk (via a temp file).
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp_path.replace(path)


def set_role_for_file(hci_path: Path, role: str, missing_only: bool) -> None:
    """
    Set or update HCI_v1_role in a single .hci.json file.
    """
    try:
        data = load_hci(hci_path)
    except Exception as e:
        print(f"[WARN] Failed to read {hci_path}: {e}")
        return

    current = data.get("HCI_v1_role")

    if missing_only:
        if current is None:
            data["HCI_v1_role"] = role
            print(f"[INFO] {hci_path}: HCI_v1_role missing → set to '{role}'.")
        else:
            print(f"[INFO] {hci_path}: HCI_v1_role already '{current}', leaving as-is.")
    else:
        data["HCI_v1_role"] = role
        print(f"[INFO] {hci_path}: HCI_v1_role set to '{role}' (was '{current}').")

    try:
        save_hci(hci_path, data)
    except Exception as e:
        print(f"[WARN] Failed to write {hci_path}: {e}")


def set_role_for_root(root: Path, role: str, missing_only: bool) -> None:
    """
    Walk a root directory and update all *.hci.json files under it.
    """
    if not root.exists():
        print(f"[WARN] Root does not exist; skipping: {root}")
        return

    count = 0
    for hci_path in root.rglob("*.hci.json"):
        set_role_for_file(hci_path, role, missing_only)
        count += 1

    print(f"[DONE] Updated {count} file(s) under {root}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set or update HCI_v1_role in one or many .hci.json files."
    )
    parser.add_argument(
        "--hci",
        help="Path to a single .hci.json file to update.",
    )
    parser.add_argument(
        "--root",
        action="append",
        help="Root directory containing .hci.json files (can be passed multiple times).",
    )
    parser.add_argument(
        "--role",
        choices=["wip", "benchmark", "other"],
        default="wip",
        help="Role to set (default: wip).",
    )
    parser.add_argument(
        "--if-missing-only",
        dest="if_missing_only",
        action="store_true",
        help="Only set HCI_v1_role if it is missing; do not overwrite existing values.",
    )

    args = parser.parse_args()

    if not args.hci and not args.root:
        parser.error("You must provide either --hci or --root (or both).")

    if args.hci:
        path = Path(args.hci)
        set_role_for_file(path, args.role, args.if_missing_only)

    if args.root:
        for root_str in args.root:
            root_path = Path(root_str)
            set_role_for_root(root_path, args.role, args.if_missing_only)


if __name__ == "__main__":
    main()
