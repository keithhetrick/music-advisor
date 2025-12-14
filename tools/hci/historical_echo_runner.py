#!/usr/bin/env python3
"""
historical_echo_runner.py

Opt-in wrapper to emit canonical Historical Echo artifacts plus manifest into a
content-addressed layout. Default HCI flow remains unchanged; this runner is
intended for reproducible/offline delivery.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ma_config.paths import get_historical_echo_db_path
from tools.cas_utils import build_cas_path, canonical_json_bytes, sha256_hex
from tools.hci_echo_probe_from_spine_v1 import run_echo_probe_for_features


ProbeFn = Callable[..., Dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_file_sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_config_hash(payload: Dict[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(payload))


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _default_probe(features_path: str, **kwargs: Any) -> Dict[str, Any]:
    return run_echo_probe_for_features(features_path=features_path, **kwargs)


def run(
    *,
    features_path: Path,
    out_root: Path,
    schema_id: str = "historical_echo.v1",
    manifest_schema_id: str = "historical_echo_manifest.v1",
    track_id: Optional[str] = None,
    run_id: Optional[str] = None,
    config_hash: Optional[str] = None,
    db_path: Optional[Path] = None,
    db_hash: Optional[str] = None,
    probe_fn: ProbeFn = _default_probe,
    probe_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Path]:
    """
    Compute Historical Echo and write canonical artifact + manifest into CAS.

    Returns mapping of written paths.
    """
    features_path = features_path.expanduser().resolve()
    if not features_path.is_file():
        raise FileNotFoundError(f"features file not found: {features_path}")

    db_path = db_path.expanduser().resolve() if db_path else get_historical_echo_db_path()
    probe_kwargs = probe_kwargs or {}
    track_id = track_id or features_path.stem
    run_id = run_id or str(uuid4())

    features_obj = _load_json(features_path)
    source_hash = sha256_hex(canonical_json_bytes(features_obj))

    config_material = {
        "schema_id": schema_id,
        "manifest_schema_id": manifest_schema_id,
        "db_path": str(db_path),
        "probe_kwargs": probe_kwargs,
    }
    config_hash = config_hash or _compute_config_hash(config_material)
    db_hash = db_hash or _compute_file_sha256(db_path)

    echo_payload = probe_fn(features_path=str(features_path), db=str(db_path), **probe_kwargs)
    # Inject required metadata
    echo_payload = dict(echo_payload)
    echo_payload.update(
        {
            "schema_id": schema_id,
            "track_id": track_id,
            "run_id": run_id,
            "source_hash": source_hash,
            "config_hash": config_hash,
            "db_hash": db_hash,
            "generated_at": _now_iso(),
        }
    )

    # Prepare CAS destinations
    artifact_path = build_cas_path(out_root, config_hash, source_hash, "historical_echo.json")
    manifest_path = build_cas_path(out_root, config_hash, source_hash, "manifest.json")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    artifact_bytes = canonical_json_bytes(echo_payload)
    artifact_sha = sha256_hex(artifact_bytes)
    artifact_path.write_bytes(artifact_bytes)

    manifest = {
        "schema_id": manifest_schema_id,
        "source_hash": source_hash,
        "config_hash": config_hash,
        "db_hash": db_hash,
        "runner": {
            "runner_name": "historical_echo_runner",
            "version": "unversioned",  # optionally set by caller
            "input_features_path": str(features_path),
        },
        "artifact": {
            "path": "historical_echo.json",
            "sha256": artifact_sha,
            "etag": artifact_sha,
            "size": len(artifact_bytes),
        },
    }
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)

    return {
        "artifact": artifact_path,
        "manifest": manifest_path,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Emit canonical Historical Echo artifact + manifest into CAS (opt-in).")
    p.add_argument("--features", required=True, help="Path to input .features.json")
    p.add_argument("--out-root", default="data/echo_cas", help="CAS root (default: data/echo_cas)")
    p.add_argument("--schema-id", default="historical_echo.v1", help="Schema id to embed in artifact.")
    p.add_argument("--manifest-schema-id", default="historical_echo_manifest.v1", help="Schema id to embed in manifest.")
    p.add_argument("--track-id", default=None, help="Optional track id override (default: features stem).")
    p.add_argument("--run-id", default=None, help="Optional run id override (default: random uuid4).")
    p.add_argument("--config-hash", default=None, help="Optional config hash override (default: auto from probe params).")
    p.add_argument("--db", default=None, help="Historical Echo DB path (default honors MA_DATA_ROOT).")
    p.add_argument("--db-hash", default=None, help="Optional DB hash override (default: auto if --auto-db-hash set).")
    p.add_argument("--auto-db-hash", action="store_true", help="Compute db hash automatically (may be slow on large DBs).")
    p.add_argument("--tiers", default="tier1_modern", help="Comma list of tiers to search.")
    p.add_argument("--table", default="spine_master_v1_lanes", help="Spine table name.")
    p.add_argument("--echo-tier", default="EchoTier_1_YearEnd_Top40", help="Echo tier filter.")
    p.add_argument("--year-min", type=int, default=1985, help="Minimum spine year.")
    p.add_argument("--year-max", type=int, default=2020, help="Maximum spine year.")
    p.add_argument("--top-k", type=int, default=10, help="Neighbors to return.")
    p.add_argument("--use-tempo-confidence", action="store_true", help="Down-weight tempo when confidence is low.")
    p.add_argument("--tempo-confidence-threshold", type=float, default=0.4, help="Tempo confidence threshold.")
    p.add_argument("--tempo-weight-low", type=float, default=0.3, help="Tempo weight when confidence is low.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    probe_kwargs = {
        "table": args.table,
        "echo_tier": args.echo_tier,
        "year_min": args.year_min,
        "year_max": args.year_max,
        "top_k": args.top_k,
        "tiers": args.tiers,
        "use_tempo_confidence": bool(args.use_tempo_confidence),
        "tempo_confidence_threshold": args.tempo_confidence_threshold,
        "tempo_weight_low": args.tempo_weight_low,
    }
    db_path = Path(args.db).expanduser().resolve() if args.db else get_historical_echo_db_path()
    db_hash = args.db_hash
    if args.auto_db_hash and not db_hash:
        db_hash = _compute_file_sha256(db_path)

    paths = run(
        features_path=Path(args.features),
        out_root=Path(args.out_root),
        schema_id=args.schema_id,
        manifest_schema_id=args.manifest_schema_id,
        track_id=args.track_id,
        run_id=args.run_id,
        config_hash=args.config_hash,
        db_path=db_path,
        db_hash=db_hash,
        probe_kwargs=probe_kwargs,
    )
    print(f"[echo_runner] wrote artifact: {paths['artifact']}")
    print(f"[echo_runner] wrote manifest: {paths['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
