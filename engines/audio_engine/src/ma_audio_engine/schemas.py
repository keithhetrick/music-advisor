"""
Minimal schema helpers for features/HCI/GPT artifacts.
Provides typed containers and JSON helpers to reduce ad-hoc dict munging.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional, List
import json


@dataclass
class FeaturePipelineMeta:
    source_hash: str = ""
    config_fingerprint: str = ""
    pipeline_version: str = ""


@dataclass
class Features:
    source_audio: str
    tempo_bpm: Optional[float]
    key: Optional[str]
    mode: Optional[str]
    loudness_LUFS: Optional[float]
    tempo_backend: str
    feature_pipeline_meta: FeaturePipelineMeta
    tempo_backend_detail: Optional[str] = None

    @classmethod
    def from_json(cls, path: Path) -> "Features":
        data = json.loads(path.read_text())
        meta = data.get("feature_pipeline_meta") or {}
        return cls(
            source_audio=data.get("source_audio", ""),
            tempo_bpm=data.get("tempo_bpm"),
            key=data.get("key"),
            mode=data.get("mode"),
            loudness_LUFS=data.get("loudness_LUFS"),
            tempo_backend=data.get("tempo_backend", "unknown"),
            tempo_backend_detail=data.get("tempo_backend_detail"),
            feature_pipeline_meta=FeaturePipelineMeta(
                source_hash=meta.get("source_hash", ""),
                config_fingerprint=meta.get("config_fingerprint", ""),
                pipeline_version=meta.get("pipeline_version", ""),
            ),
        )


@dataclass
class HCI:
    HCI_v1_final_score: Optional[float]
    HCI_v1_role: str
    feature_pipeline_meta: FeaturePipelineMeta
    historical_echo_v1: dict = field(default_factory=dict)
    historical_echo_meta: dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: Path) -> "HCI":
        data = json.loads(path.read_text())
        meta = data.get("feature_pipeline_meta") or {}
        return cls(
            HCI_v1_final_score=data.get("HCI_v1_final_score"),
            HCI_v1_role=data.get("HCI_v1_role", "unknown"),
            feature_pipeline_meta=FeaturePipelineMeta(
                source_hash=meta.get("source_hash", ""),
                config_fingerprint=meta.get("config_fingerprint", ""),
                pipeline_version=meta.get("pipeline_version", ""),
            ),
            historical_echo_v1=data.get("historical_echo_v1") or {},
            historical_echo_meta=data.get("historical_echo_meta") or {},
        )


@dataclass
class GPTRich:
    text: str
    hci_score: Optional[float]
    philosophy: Optional[str] = None
    echo_summary: Optional[str] = None
    audio_json: Optional[Dict[str, Any]] = None

    @classmethod
    def from_text(cls, path: Path, hci_score: Optional[float] = None) -> "GPTRich":
        text = path.read_text()
        philosophy = None
        echo_summary = None
        audio_json = None
        marker = "/audio import"
        idx = text.find(marker)
        if idx != -1:
            json_start = text.find("{", idx)
            if json_start != -1:
                try:
                    audio_json = json.loads(text[json_start:])
                except Exception:
                    audio_json = None
        for line in text.splitlines():
            if line.startswith("# PHILOSOPHY:"):
                philosophy = line.replace("# PHILOSOPHY:", "").strip()
            if line.startswith("# ECHO SUMMARY:"):
                echo_summary = line.replace("# ECHO SUMMARY:", "").strip()
        return cls(text=text, hci_score=hci_score, philosophy=philosophy, echo_summary=echo_summary, audio_json=audio_json)


@dataclass
class CLIENTRich(GPTRich):
    """Client-named rich payload; structure mirrors GPTRich."""

    @classmethod
    def from_text(cls, path: Path, hci_score: Optional[float] = None) -> "CLIENTRich":
        base = GPTRich.from_text(path, hci_score=hci_score)
        return cls(
            text=base.text,
            hci_score=base.hci_score,
            philosophy=base.philosophy,
            echo_summary=base.echo_summary,
            audio_json=base.audio_json,
        )


@dataclass
class Neighbor:
    year: int
    artist: str
    title: str
    distance: float
    tier: str
    tempo: Optional[float] = None
    valence: Optional[float] = None
    energy: Optional[float] = None
    loudness: Optional[float] = None


@dataclass
class HistoricalEcho:
    primary_decade: Optional[str]
    primary_decade_neighbor_count: int
    top_neighbor: dict
    neighbors: list

    @classmethod
    def from_json(cls, payload: dict) -> "HistoricalEcho":
        return cls(
            primary_decade=payload.get("primary_decade"),
            primary_decade_neighbor_count=int(payload.get("primary_decade_neighbor_count") or 0),
            top_neighbor=payload.get("top_neighbor") or {},
            neighbors=payload.get("neighbors") or [],
        )


def dump_json(path: Path, obj: Any) -> None:
    if hasattr(obj, "__dataclass_fields__"):
        payload = asdict(obj)
    else:
        payload = obj
    path.write_text(json.dumps(payload, indent=2))


def lint_sidecar_payload(payload: dict) -> List[str]:
    """
    Lightweight validation for tempo sidecar JSON payloads.
    Returns a list of warning strings (empty = clean enough).
    """
    warnings: List[str] = []
    if not isinstance(payload, dict):
        return ["not_a_mapping"]

    backend = payload.get("backend")
    if backend is None or not isinstance(backend, str):
        warnings.append("missing:backend")

    tempo = payload.get("tempo") or payload.get("tempo_bpm")
    if tempo is None:
        warnings.append("missing:tempo")
    else:
        try:
            t = float(tempo)
            if t < 40 or t > 240:
                warnings.append("tempo_out_of_range")
        except Exception:
            warnings.append("tempo_not_numeric")

    mode = payload.get("mode")
    if mode and mode not in ("major", "minor", "unknown"):
        warnings.append("mode_invalid")

    beats = payload.get("beats_sec")
    beats_count = payload.get("beats_count")
    if isinstance(beats, list) and beats_count is not None:
        try:
            if int(beats_count) != len(beats):
                warnings.append("beats_count_mismatch")
        except Exception:
            warnings.append("beats_count_non_numeric")

    conf_bounds = payload.get("tempo_confidence_bounds")
    if conf_bounds is not None:
        if not (isinstance(conf_bounds, list) and len(conf_bounds) == 2):
            warnings.append("tempo_confidence_bounds_invalid")

    return warnings


def render_gpt_rich(
    text: str,
    updated_audio_json: Optional[Dict[str, Any]],
    *,
    prefix_lines: Optional[List[str]] = None,
    tail: Optional[str] = None,
) -> str:
    """
    Reconstruct a .gpt.rich.txt with updated /audio import JSON.
    Preserves existing headers (minus PHILOSOPHY/ECHO SUMMARY if new ones are provided).
    """
    if updated_audio_json is None:
        return text
    marker = "/audio import"
    idx = text.find(marker)
    if idx == -1:
        return text
    json_start = text.find("{", idx)
    if json_start == -1:
        return text
    header_text = text[:idx]
    import_prefix = text[idx:json_start]
    if prefix_lines:
        # Replace the header entirely with the provided lines.
        new_header = "\n".join(prefix_lines)
    else:
        new_header = header_text.rstrip("\n")
    if new_header:
        new_header += "\n"
    body = f"{new_header}{import_prefix}{json.dumps(updated_audio_json, indent=2)}"
    if tail:
        body = f"{body}\n\n{tail}"
    return body


def lint_gpt_rich_text(text: str) -> List[str]:
    """
    Basic linter for *.gpt.rich.txt content.
    Checks presence of /audio import block and critical keys inside it.
    Returns a list of warning strings.
    """
    warnings: List[str] = []
    marker = "/audio import"
    idx = text.find(marker)
    if idx == -1:
        return ["missing:audio_import"]
    json_start = text.find("{", idx)
    if json_start == -1:
        return ["missing:audio_import_json"]
    # Extract just the JSON object that immediately follows the marker to avoid
    # trailing text (e.g., echo summaries) breaking parsing.
    brace_depth = 0
    end_idx = None
    for i, ch in enumerate(text[json_start:], start=json_start):
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0:
                end_idx = i + 1
                break
    if end_idx is None:
        return ["invalid:audio_import_json"]
    try:
        payload = json.loads(text[json_start:end_idx])
    except Exception:
        return ["invalid:audio_import_json"]
    # Tighten required fields inside the audio import payload
    feat = payload.get("features") or {}
    feat_full = payload.get("features_full") or {}
    if "runtime_sec" not in feat:
        warnings.append("missing:features.runtime_sec")
    if "runtime_sec" not in feat_full:
        warnings.append("missing:features_full.runtime_sec")
    for key in ("historical_echo_v1", "historical_echo_meta", "feature_pipeline_meta"):
        if key not in payload:
            warnings.append(f"missing:{key}")
    return warnings


def lint_client_rich_text(text: str) -> List[str]:
    """
    Alias for client-named rich text; structure matches GPT rich.
    """
    return lint_gpt_rich_text(text)
