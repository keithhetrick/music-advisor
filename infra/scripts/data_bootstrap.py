#!/usr/bin/env python3
"""
Data bootstrap script.

- Reads infra/scripts/data_manifest.json (explicit allowlist of S3/HTTPS assets).
- Downloads each asset and verifies SHA256 if provided.
- Writes under MA_DATA_ROOT/public/... (default: data/public/...).
- Never touches data/private or data/features_output.

Usage:
  python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json
  python infra/scripts/data_bootstrap.py --manifest https://.../data_manifest.json

Manifest schema (JSON):
{
  "version": 1,
  "assets": [
    {
      "name": "market_norms_us_pop",
      "target_path": "data/public/market_norms/market_norms_us_pop.json",
      "url": "https://...",
      "sha256": "optional checksum",
      "optional": false
    }
  ]
}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse
from urllib.request import urlopen


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Download data assets per manifest.")
    ap.add_argument("--manifest", required=True, help="Path or URL to data_manifest.json")
    ap.add_argument("--force", action="store_true", help="Re-download even if file exists")
    return ap.parse_args()


def _load_manifest(path_or_url: str) -> Dict[str, Any]:
    parsed = urlparse(path_or_url)
    if parsed.scheme in ("http", "https"):
        with urlopen(path_or_url) as resp:
            return json.loads(resp.read().decode("utf-8"))
    p = Path(path_or_url)
    return json.loads(p.read_text())


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as resp, dest.open("wb") as out:
        out.write(resp.read())


def main() -> int:
    args = parse_args()
    data_root = Path(os.environ.get("MA_DATA_ROOT", "data"))
    manifest = _load_manifest(args.manifest)
    assets = manifest.get("assets", [])
    if not assets:
        print("[data-bootstrap] manifest has no assets", file=sys.stderr)
        return 1

    for entry in assets:
        name = entry.get("name", "")
        url = entry.get("url", "")
        target = Path(entry.get("target_path", ""))
        if target.is_absolute():
            dest = target
        elif target.parts and target.parts[0] == "data":
            dest = data_root.joinpath(*target.parts[1:])
        else:
            dest = data_root / target
        optional = bool(entry.get("optional", False))
        sha256 = entry.get("sha256", "")
        if not url or not dest:
            print(f"[data-bootstrap] skip invalid entry: {entry}", file=sys.stderr)
            continue
        if dest.exists() and not args.force:
            if sha256:
                current = _sha256(dest)
                if current == sha256:
                    print(f"[data-bootstrap] {name} already present and matches checksum")
                    continue
                else:
                    print(f"[data-bootstrap] {name} present but checksum mismatch; re-downloading")
            else:
                print(f"[data-bootstrap] {name} already present (no checksum to verify); skip")
                continue
        try:
            print(f"[data-bootstrap] downloading {name} -> {dest}")
            _download(url, dest)
            if sha256:
                current = _sha256(dest)
                if current != sha256:
                    raise RuntimeError(f"checksum mismatch for {name}: expected {sha256}, got {current}")
        except Exception as e:
            msg = f"[data-bootstrap] failed {name}: {e}"
            if optional:
                print(msg, file=sys.stderr)
                continue
            else:
                print(msg, file=sys.stderr)
                return 1
    print("[data-bootstrap] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
