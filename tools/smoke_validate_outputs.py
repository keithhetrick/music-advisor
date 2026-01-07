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
import os
from pathlib import Path
from typing import Any, Tuple


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


def _require(cond: bool, msg: str) -> int:
    if not cond:
        return _fail(msg)
    return 0


def validate_features(path: Path) -> Tuple[int, dict[str, Any]]:
    data, err = _load_json(path)
    if err:
        return _fail(f"{path}: {err}"), {}
    backend = data.get("tempo_backend")
    if backend not in {"librosa", "external"}:
        return _fail(f"{path}: tempo_backend invalid ({backend})"), {}
    detail = data.get("tempo_backend_detail")
    if not isinstance(detail, str) or not detail:
        return _fail(f"{path}: tempo_backend_detail missing/invalid"), {}
    meta = data.get("tempo_backend_meta")
    if not isinstance(meta, dict) or "backend" not in meta:
        return _fail(f"{path}: tempo_backend_meta missing backend"), {}
    forbidden = {"external_sidecar", "missing", "stub", "none"}
    if detail in forbidden or str(meta.get("backend")) in forbidden:
        return _fail(f"{path}: tempo backend detail/meta contains forbidden value"), {}
    if "qa_status" not in data:
        return _fail(f"{path}: qa_status missing"), {}
    if "qa_gate" not in data:
        return _fail(f"{path}: qa_gate missing"), {}
    fpm = data.get("feature_pipeline_meta")
    if not isinstance(fpm, dict):
        return _fail(f"{path}: feature_pipeline_meta missing/invalid"), {}
    _ok(f"{path.name} tempo backend fields sane")
    return 0, data


def validate_client(path: Path) -> int:
    data, err = _load_json(path)
    if err:
        return _fail(f"{path}: {err}")
    feats = data.get("features") or {}
    if "runtime_sec" not in feats:
        return _fail(f"{path}: features.runtime_sec missing")
    try:
        if feats["runtime_sec"] is None or float(feats["runtime_sec"]) < 0:
            return _fail(f"{path}: features.runtime_sec invalid ({feats['runtime_sec']})")
    except Exception:
        return _fail(f"{path}: features.runtime_sec not numeric ({feats['runtime_sec']})")
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
    synth_client = root / "smoke.synth.client.json"
    run_summary = root / "run_summary.json"

    for p in [features, merged, client, rich_txt, hci]:
        if not p.exists():
            rc |= _fail(f"missing required file: {p}")
    if rc:
        return rc

    # Features
    rc_features, feats_data = validate_features(features)
    rc |= rc_features
    # merged parse
    _, err = _load_json(merged)
    rc |= _fail(f"{merged}: {err}") if err else 0
    if not err:
        _ok(f"{merged.name} parseable")
    # client
    rc |= validate_client(client)
    # hci
    _, err = _load_json(hci)
    rc |= _fail(f"{hci}: {err}") if err else 0
    if not err:
        _ok(f"{hci.name} parseable")
    # rich txt
    try:
        rich_txt.read_text()
        _ok(f"{rich_txt.name} readable")
    except Exception as e:  # noqa: BLE001
        rc |= _fail(f"{rich_txt}: read error {e}")

    # Optional run summary
    if run_summary.exists():
        _, err = _load_json(run_summary)
        rc |= _fail(f"{run_summary}: {err}") if err else 0
        if not err:
            _ok(f"{run_summary.name} parseable")

    # Synth client should never clobber main client
    if synth_client.exists():
        rc |= _require(synth_client != client, f"synth client path equals main client: {synth_client}")
        try:
            synth_stat = synth_client.stat()
            client_stat = client.stat()
            if os.path.samestat(synth_stat, client_stat):
                rc |= _fail("synth client shares inode with main client (overwrite suspected)")
        except Exception:
            pass
        _, err = _load_json(synth_client)
        rc |= _fail(f"{synth_client}: {err}") if err else 0
        if not err:
            _ok(f"{synth_client.name} parseable and distinct")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
