"""
Lightweight validators for pipeline artifacts.

Usage:
  python3 tools/validate_io.py --root features_output/2025/11/29/Some\ Track
  python3 tools/validate_io.py --file path/to/file.client.json

This is conservative: it checks shape, key presence, and basic value sanity, and
reports warnings instead of exiting non-zero so it can be used in CI or as a
post-run audit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from shared.config.paths import get_features_output_root
from typing import Dict, List, Tuple


def _load_json(path: Path) -> Tuple[Dict, List[str]]:
    warnings: List[str] = []
    try:
        with path.open() as f:
            data = json.load(f)
    except Exception as exc:  # broad by design; this is a validator
        warnings.append(f"{path}: failed to parse JSON ({exc})")
        return {}, warnings
    if not isinstance(data, dict):
        warnings.append(f"{path}: expected top-level object, found {type(data).__name__}")
    return data, warnings


def validate_features(path: Path) -> List[str]:
    data, warnings = _load_json(path)
    if not data:
        return warnings
    required = ["source_audio", "sample_rate", "duration_sec"]
    for key in required:
        if key not in data:
            warnings.append(f"{path}: missing expected key '{key}'")
    # Basic numeric sanity
    dur = data.get("duration_sec")
    if isinstance(dur, (int, float)) and dur <= 0:
        warnings.append(f"{path}: duration_sec <= 0 ({dur})")
    sr = data.get("sample_rate")
    if isinstance(sr, (int, float)) and sr < 8000:
        warnings.append(f"{path}: sample_rate unusually low ({sr})")
    return warnings


def validate_merged(path: Path) -> List[str]:
    data, warnings = _load_json(path)
    if not data:
        return warnings
    required = ["source_audio", "duration_sec", "tempo_bpm"]
    for key in required:
        if key not in data:
            warnings.append(f"{path}: missing expected key '{key}'")
    return warnings


def validate_client_json(path: Path) -> List[str]:
    data, warnings = _load_json(path)
    if not data:
        return warnings
    required = ["generated_by", "inputs", "features", "features_full", "track_title"]
    for key in required:
        if key not in data:
            warnings.append(f"{path}: missing expected key '{key}'")
    return warnings


def validate_client_rich(path: Path) -> List[str]:
    warnings: List[str] = []
    try:
        content = path.read_text()
    except Exception as exc:
        return [f"{path}: failed to read ({exc})"]
    if "/audio import" not in content:
        warnings.append(f"{path}: missing '/audio import' marker")
    if "HCI_V1_FINAL" not in content:
        warnings.append(f"{path}: missing HCI header line")
    return warnings


def collect_targets(root: Path, explicit: Path | None) -> List[Tuple[Path, str]]:
    targets: List[Tuple[Path, str]] = []
    if explicit:
        suffix = explicit.suffix.lower()
        if suffix.endswith(".json"):
            if explicit.name.endswith(".features.json"):
                targets.append((explicit, "features"))
            elif explicit.name.endswith(".merged.json"):
                targets.append((explicit, "merged"))
            elif explicit.name.endswith(".client.json"):
                targets.append((explicit, "client_json"))
        elif explicit.name.endswith(".client.txt"):
            targets.append((explicit, "client_rich"))
        return targets

    for path in root.rglob("*"):
        name = path.name
        if name.endswith(".features.json"):
            targets.append((path, "features"))
        elif name.endswith(".merged.json"):
            targets.append((path, "merged"))
        elif name.endswith(".client.json"):
            targets.append((path, "client_json"))
        elif name.endswith(".client.txt"):
            targets.append((path, "client_rich"))
    return targets


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate pipeline artifacts (features/merged/client).")
    default_root = get_features_output_root()
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help=f"Root folder to scan recursively (default: {default_root})",
    )
    parser.add_argument("--file", type=Path, help="Validate a single file")
    args = parser.parse_args(argv)

    if not args.root and not args.file:
        parser.error("Provide --root or --file")

    targets = collect_targets(args.root or args.file.parent, args.file)
    all_warnings: List[str] = []
    for path, kind in targets:
        if kind == "features":
            all_warnings.extend(validate_features(path))
        elif kind == "merged":
            all_warnings.extend(validate_merged(path))
        elif kind == "client_json":
            all_warnings.extend(validate_client_json(path))
        elif kind == "client_rich":
            all_warnings.extend(validate_client_rich(path))

    if all_warnings:
        print("\n".join(all_warnings))
        print(f"\nCompleted with {len(all_warnings)} warning(s).")
        return 1
    print("All checked artifacts passed basic validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
