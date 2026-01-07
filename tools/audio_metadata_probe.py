"""
Audio metadata probe: best-effort, read-only extraction of container details and tags.

Usage:
- Import: `from tools.audio_metadata_probe import extract_audio_metadata`
- CLI: `python -m tools.audio_metadata_probe file1.wav file2.flac`
  - Prints a JSON array of per-file metadata.
  - Continues past per-file failures; exits non-zero if any file hit a fatal error.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from shared.security import subprocess as sec_subprocess
from shared.security.config import CONFIG

try:
    import mutagen  # type: ignore[import-not-found]

    _HAS_MUTAGEN = True
except Exception:
    mutagen = None
    _HAS_MUTAGEN = False


SUPPORTED_EXTS = {".wav", ".aiff", ".aif", ".flac", ".mp3", ".m4a", ".ogg"}
DAW_SIGNATURES: List[Tuple[str, str]] = [
    ("logic pro", "Logic Pro"),
    ("apple logic", "Logic Pro"),
    ("logic", "Logic Pro"),
    ("pro tools", "Pro Tools"),
    ("ableton live", "Ableton Live"),
    ("ableton", "Ableton Live"),
    ("cubase", "Cubase"),
    ("nuendo", "Nuendo"),
    ("reaper", "REAPER"),
    ("studio one", "Studio One"),
    ("fl studio", "FL Studio"),
    ("fruity loops", "FL Studio"),
    ("garageband", "GarageBand"),
    ("bitwig", "Bitwig Studio"),
    ("audition", "Adobe Audition"),
    ("sound forge", "Sound Forge"),
    ("samplitude", "Samplitude"),
    ("reason", "Reason"),
    ("bandlab", "BandLab"),
    ("tracktion", "Tracktion"),
    ("logic x", "Logic Pro"),
]


def extract_audio_metadata(path: Path | str) -> Dict[str, Any]:
    """
    Probe an audio file for container info, tags, and DAW hints.
    Returns a JSON-serializable dict; never raises on per-file errors.
    """
    p = Path(path)
    result: Dict[str, Any] = {
        "path": str(p),
        "exists": p.exists(),
        "is_file": p.is_file(),
        "extension": p.suffix.lower(),
    }
    try:
        result["size_bytes"] = p.stat().st_size if p.exists() else None
    except Exception:
        result["size_bytes"] = None

    if not p.exists():
        result["error"] = "file_not_found"
        return result
    if not p.is_file():
        result["error"] = "not_a_file"
        return result
    if result["extension"] and result["extension"] not in SUPPORTED_EXTS:
        result["unsupported_extension"] = True

    ffprobe_data = _extract_ffprobe(p)
    if ffprobe_data:
        result["ffprobe"] = ffprobe_data

    tag_data = _extract_tags(p)
    if tag_data:
        result["tags"] = tag_data

    derived = _derive(ffprobe_data, tag_data)
    if derived:
        result["derived"] = derived

    return result


def _extract_ffprobe(path: Path) -> Dict[str, Any]:
    """
    Run ffprobe to collect container/stream metadata.
    """
    if shutil.which("ffprobe") is None:
        return {"error": "ffprobe_not_found"}
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        completed = sec_subprocess.run_safe(
            cmd,
            allow_roots=CONFIG.allowed_binary_roots,
            timeout=CONFIG.subprocess_timeout,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout or "{}")
        return payload
    except Exception as exc:  # noqa: BLE001
        # Avoid failing the probe; capture the failure reason.
        return {"error": f"ffprobe_failed: {exc.__class__.__name__}: {exc}"}


def _normalize_tag_value(val: Any) -> Any:
    """
    Convert mutagen tag values to JSON-serializable primitives.
    """
    if isinstance(val, (list, tuple, set)):
        return [_normalize_tag_value(v) for v in val]
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8", errors="replace")
        except Exception:
            return str(val)
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    return str(val)


def _extract_tags(path: Path) -> Dict[str, Any]:
    """
    Extract tags using mutagen when available. Does not fail the whole probe.
    """
    if not _HAS_MUTAGEN or mutagen is None:
        return {"error": "mutagen_not_available"}
    try:
        audio = mutagen.File(path, easy=False)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"mutagen_open_failed: {exc.__class__.__name__}: {exc}"}
    if audio is None:
        return {"error": "mutagen_unable_to_parse"}

    tags: Dict[str, Any] = {}
    if audio.tags:
        for key, value in audio.tags.items():
            tags[str(key)] = _normalize_tag_value(value)

    info: Dict[str, Any] = {}
    info_fields = [
        "length",
        "bitrate",
        "sample_rate",
        "channels",
        "bits_per_sample",
        "bit_depth",
    ]
    for field in info_fields:
        if hasattr(audio.info, field):
            val = getattr(audio.info, field)
            if val is not None:
                info[field] = val
    # Some formats expose encoder/encoding_tool via info; keep it if present.
    for field in ("encoder_info", "encoding_tool", "vendor"):
        if hasattr(audio.info, field):
            val = getattr(audio.info, field)
            if val:
                info[field] = _normalize_tag_value(val)

    mutagen_data: Dict[str, Any] = {}
    if tags:
        mutagen_data["tags"] = tags
    if info:
        mutagen_data["info"] = info
    if not mutagen_data:
        mutagen_data["note"] = "mutagen_loaded_no_tags"
    return mutagen_data


def _iter_strings(source: Dict[str, Any], prefix: str) -> Iterable[Tuple[str, str]]:
    for key, value in source.items():
        if isinstance(value, str):
            yield (f"{prefix}.{key}", value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, str):
                    yield (f"{prefix}.{key}", item)
        elif isinstance(value, dict):
            # Shallow dict walk; tag dictionaries tend to be flat.
            for sub_key, sub_val in value.items():
                if isinstance(sub_val, str):
                    yield (f"{prefix}.{key}.{sub_key}", sub_val)


def _derive(ffprobe_data: Optional[Dict[str, Any]], tag_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    derived: Dict[str, Any] = {}

    # Basic container summary from ffprobe if present.
    if ffprobe_data and isinstance(ffprobe_data, dict):
        fmt = ffprobe_data.get("format") or {}
        streams = ffprobe_data.get("streams") or []
        if fmt:
            summary: Dict[str, Any] = {}
            for key in ("format_name", "format_long_name", "duration", "bit_rate", "size"):
                if key in fmt:
                    summary[key] = fmt[key]
            # Capture primary audio stream properties.
            audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
            if audio_streams:
                a0 = audio_streams[0]
                for key in ("codec_name", "codec_long_name", "sample_rate", "channels", "bits_per_sample", "bit_rate"):
                    if key in a0:
                        summary[f"stream_{key}"] = a0[key]
            if summary:
                derived["container"] = summary

    daw_strings: List[Tuple[str, str]] = []
    if ffprobe_data and isinstance(ffprobe_data, dict):
        fmt_tags = {}
        if isinstance(ffprobe_data.get("format"), dict):
            fmt_tags = ffprobe_data["format"].get("tags") or {}
        if fmt_tags:
            daw_strings.extend(_iter_strings(fmt_tags, "ffprobe.format.tags"))
        streams = ffprobe_data.get("streams") or []
        for idx, stream in enumerate(streams):
            if isinstance(stream, dict) and stream.get("tags"):
                prefix = f"ffprobe.streams[{idx}].tags"
                daw_strings.extend(_iter_strings(stream["tags"], prefix))
    if tag_data and isinstance(tag_data, dict) and tag_data.get("tags"):
        daw_strings.extend(_iter_strings(tag_data["tags"], "mutagen.tags"))
    if tag_data and isinstance(tag_data, dict) and tag_data.get("info"):
        daw_strings.extend(_iter_strings(tag_data["info"], "mutagen.info"))

    daw_hints = _detect_daws(daw_strings)
    if daw_hints:
        derived["possible_daw"] = daw_hints

    return derived


def _detect_daws(candidates: Iterable[Tuple[str, str]]) -> List[Dict[str, Any]]:
    matches: Dict[str, Dict[str, Any]] = {}
    for field, value in candidates:
        lower_val = value.lower()
        for needle, label in DAW_SIGNATURES:
            if needle in lower_val:
                record = matches.setdefault(label, {"name": label, "evidence": []})
                record["evidence"].append({"field": field, "value": value})
    return list(matches.values())


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe audio files for metadata (read-only).")
    parser.add_argument("paths", nargs="+", help="Audio files to inspect.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    results = []
    exit_code = 0
    for raw_path in args.paths:
        try:
            meta = extract_audio_metadata(raw_path)
            if meta.get("error") or (meta.get("ffprobe", {}).get("error")):
                exit_code = 1
            results.append(meta)
        except Exception as exc:  # noqa: BLE001
            exit_code = 1
            results.append({"path": raw_path, "error": f"probe_failed: {exc.__class__.__name__}: {exc}"})
    json.dump(results, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
