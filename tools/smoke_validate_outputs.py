#!/usr/bin/env python3
"""
Lightweight local validator for smoke outputs.

Usage:
  python tools/smoke_validate_outputs.py --root <OUT_DIR>

No external deps; intended for manual sanity checks only (not wired into CI).
"""

import argparse
import json
import sys
from pathlib import Path


def _load_json(path: Path):
    try:
        return json.loads(path.read_text()), None
    except Exception as e:  # noqa: BLE001
        return None, f"parse error: {e}"


def _fail(msg: str) -> int:
    print(f"[ERR] {msg}")
    return 1


def _ok(msg: str) -> None:
    print(f"[ok] {msg}")


def validate_features(path: Path) -> int:
    data, err = _load_json(path)
    if err:
        return _fail(f"{path}: {err}")
    backend = data.get("tempo_backend")
    if backend not in {"librosa", "external"}:
        return _fail(f"{path}: tempo_backend invalid ({backend})")
    detail = data.get("tempo_backend_detail")
    if not isinstance(detail, str) or not detail:
        return _fail(f"{path}: tempo_backend_detail missing/invalid")
    meta = data.get("tempo_backend_meta")
    if not isinstance(meta, dict) or "backend" not in meta:
        return _fail(f"{path}: tempo_backend_meta missing backend")
    forbidden = {"external_sidecar", "missing", "stub", "none"}
    if detail in forbidden or str(meta.get("backend")) in forbidden:
        return _fail(f"{path}: tempo backend detail/meta contains forbidden value")
    _ok(f"{path.name} tempo backend fields sane")
    return 0


def validate_client(path: Path) -> int:
    data, err = _load_json(path)
    if err:
        return _fail(f"{path}: {err}")
    feats = data.get("features") or {}
    if "runtime_sec" not in feats:
        return _fail(f"{path}: features.runtime_sec missing")
    _ok(f"{path.name} runtime_sec present")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate smoke outputs")
    parser.add_argument("--root", required=True, help="Smoke output directory")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        return _fail(f"root not found: {root}")

    rc = 0
    features = root / "smoke.features.json"
    merged = root / "smoke.merged.json"
    client = root / "smoke.client.json"
    hci = root / "smoke.hci.json"
    rich_txt = root / "smoke.client.rich.txt"

    for p in [features, merged, client]:
        if not p.exists():
            rc |= _fail(f"missing required file: {p}")
    if rc:
        return rc

    rc |= validate_features(features)
    _, err = _load_json(merged)
    if err:
        rc |= _fail(f"{merged}: {err}")
    else:
        _ok(f"{merged.name} parseable")

    rc |= validate_client(client)

    if hci.exists():
        _, err = _load_json(hci)
        if err:
            rc |= _fail(f"{hci}: {err}")
        else:
            _ok(f"{hci.name} parseable")
    if rich_txt.exists():
        try:
            rich_txt.read_text()
            _ok(f"{rich_txt.name} readable")
        except Exception as e:  # noqa: BLE001
            rc |= _fail(f"{rich_txt}: read error {e}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
