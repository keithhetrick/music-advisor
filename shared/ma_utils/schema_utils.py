#!/usr/bin/env python3
"""
Minimal schema lint helpers (warn-only) for feature/hci/client payloads.
Non-destructive: surface missing/invalid core fields to calling code.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

from ma_audio_engine.schemas import lint_client_rich_text, lint_sidecar_payload
from jsonschema import Draft7Validator

def validate_with_schema(schema_path: Path, instance: dict) -> List[str]:
    """Validate instance against a JSON schema; return list of errors (strings)."""
    try:
        schema = json.loads(schema_path.read_text())
        Draft7Validator.check_schema(schema)
        errors = sorted(Draft7Validator(schema).iter_errors(instance), key=lambda e: e.path)
        return [f"{'/'.join(map(str, err.path)) or '<root>'}: {err.message}" for err in errors]
    except Exception as exc:  # noqa: BLE001
        return [f"schema_error:{exc}"]

def lint_features_payload(data: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    required_numeric = ["tempo_bpm", "energy", "danceability", "valence", "loudness_LUFS"]
    for key in required_numeric:
        val = data.get(key)
        if val is None:
            warnings.append(f"missing:{key}")
            continue
        try:
            float(val)
        except Exception:
            warnings.append(f"non_numeric:{key}")

    if not data.get("config_fingerprint"):
        warnings.append("missing:config_fingerprint")
    if not data.get("source_hash"):
        warnings.append("missing:source_hash")
    return warnings


def lint_hci_payload(data: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    required_fields = ["HCI_v1_final_score", "feature_pipeline_meta"]
    score = data.get("HCI_v1_final_score") or data.get("HCI_v1_score")
    try:
        float(score)
    except Exception:
        warnings.append("missing_or_non_numeric:HCI_v1_final_score")

    for f in required_fields:
        if f not in data:
            warnings.append(f"missing:{f}")
    return warnings


def lint_merged_payload(data: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    essentials = ["duration_sec", "tempo_bpm", "key", "mode", "loudness_LUFS"]
    for key in essentials:
        if data.get(key) is None:
            warnings.append(f"missing:{key}")
    return warnings


def lint_neighbors_payload(data: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    neighbors = data.get("neighbors")
    if neighbors is None:
        warnings.append("missing:neighbors")
    elif not isinstance(neighbors, list):
        warnings.append("invalid:neighbors_not_list")
    return warnings


def lint_run_summary(data: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    if not isinstance(data, dict):
        return ["invalid:summary_not_object"]
    if "artifacts" not in data:
        warnings.append("missing:artifacts")
    return warnings

def lint_pack_payload(data: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    schema = Path("schemas/pack.schema.json")
    if schema.exists():
        warnings.extend(validate_with_schema(schema, data))
    else:
        warnings.append("missing_schema:pack.schema.json")
    return warnings


def lint_json_file(path: Path, kind: str) -> Tuple[List[str], Dict[str, Any]]:
    data: Dict[str, Any] = {}
    try:
        data = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        return [f"read_error:{e}"], data

    if kind == "features":
        return lint_features_payload(data), data
    if kind == "hci":
        return lint_hci_payload(data), data
    if kind == "client_rich":
        warns = lint_client_rich_text(path.read_text())
        return warns, data
    if kind == "sidecar":
        warns = lint_sidecar_payload(data)
        return warns, data
    if kind == "merged":
        return lint_merged_payload(data), data
    if kind == "neighbors":
        warns = lint_neighbors_payload(data)
        schema = Path("schemas/neighbors.schema.json")
        if schema.exists():
            warns.extend(validate_with_schema(schema, data))
        return warns, data
    if kind == "run_summary":
        warns = lint_run_summary(data)
        schema = Path("schemas/run_summary.schema.json")
        if schema.exists():
            warns.extend(validate_with_schema(schema, data))
        return warns, data
    if kind == "pack":
        return lint_pack_payload(data), data
    return [f"unknown_kind:{kind}"], data

__all__ = [
    "lint_features_payload",
    "lint_hci_payload",
    "lint_json_file",
    "lint_merged_payload",
    "lint_neighbors_payload",
    "lint_pack_payload",
    "lint_run_summary",
    "validate_with_schema",
]
