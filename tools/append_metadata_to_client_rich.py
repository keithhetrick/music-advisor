#!/usr/bin/env python3
"""
Append a short audio metadata probe summary into a .client.rich.txt file.

We limit to container/codec basics and DAW hints to avoid duplicating values
already present in the rich text (tempo, loudness, etc.).

Usage:
  python tools/append_metadata_to_client_rich.py --track-dir <dir>
    - expects exactly one *.features.json and one *.client.rich.txt in <dir>
    - extracts source_audio from feature_pipeline_meta
    - appends a section to the rich txt if a probe succeeds

Behavior:
- Idempotent: removes any prior "# ==== AUDIO METADATA (probe) ====" block before appending.
- Safe: best-effort probe (read-only); no changes if probe fails or files missing.

Appended block example:
    # ==== AUDIO METADATA (probe) ====
    # source_audio: /path/to/song.wav
    # file_size: 12345678 bytes (~11.77 MB)
    # container: codec=flac | sr=48000 | ch=2 | bit_depth=24 | duration=214.52
    # possible_daw: Logic Pro
"""
from __future__ import annotations

import argparse
import sys
import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

# Ensure repository root and src/ on sys.path for sibling imports.
ensure_repo_root()

from tools.audio_metadata_probe import extract_audio_metadata


def _find_single(globbed) -> Optional[Path]:
    matches = list(globbed)
    return matches[0] if matches else None


def _load_source_audio_from_features(features_path: Path) -> Optional[str]:
    try:
        import json

        data = json.loads(features_path.read_text())
    except Exception:
        return None
    meta = data.get("feature_pipeline_meta") or {}
    # Prefer pipeline meta if present; fall back to top-level fields.
    audio = meta.get("source_audio") or meta.get("source_file") or data.get("source_audio") or data.get("source_file")
    return str(audio) if audio else None


def _load_source_audio_from_rich(rich_path: Path) -> Optional[str]:
    """Fallback: parse /audio import JSON from the rich file."""
    try:
        text = rich_path.read_text()
        marker = "/audio import "
        if marker in text:
            import json

            payload = text.split(marker, 1)[1]
            obj = json.loads(payload)
            return obj.get("inputs", {}).get("paths", {}).get("source_audio") or obj.get("feature_pipeline_meta", {}).get(
                "source_audio"
            )
    except Exception:
        return None
    return None


def _load_neighbor_meta(features_path: Path, track_dir: Path) -> Optional[dict]:
    try:
        import json

        data = json.loads(features_path.read_text())
    except Exception:
        data = {}
    meta = data.get("historical_echo_meta") or {}
    if isinstance(meta, dict) and meta:
        return {
            "neighbors_total": meta.get("neighbors_total"),
            "neighbor_tiers": meta.get("neighbor_tiers"),
            "neighbors_kept_inline": meta.get("neighbors_kept_inline"),
            "neighbors_file": meta.get("neighbors_file"),
        }

    # Fallback: derive from neighbors.json if present in track_dir.
    neighbor_file = _find_single(track_dir.glob("*.neighbors.json"))
    if not neighbor_file:
        return None
    try:
        import json

        ndata = json.loads(neighbor_file.read_text())
        neighbors = ndata.get("neighbors") or []
        tiers = list((ndata.get("neighbors_by_tier") or {}).keys())
        return {
            "neighbors_total": len(neighbors) if isinstance(neighbors, list) else None,
            "neighbor_tiers": tiers or None,
            "neighbors_kept_inline": min(len(neighbors), 8) if isinstance(neighbors, list) else None,
            "neighbors_file": str(neighbor_file),
        }
    except Exception:
        return None


def _format_neighbor_block(info: dict) -> list[str]:
    if not info:
        return []
    lines = [
        "# ====================================",
        "# NEIGHBOR_META:",
    ]
    if info.get("neighbors_total") is not None:
        lines.append(f"#   neighbors_total={info['neighbors_total']}")
    if info.get("neighbor_tiers"):
        lines.append(f"#   neighbor_tiers={info['neighbor_tiers']}")
    if info.get("neighbors_kept_inline") is not None:
        lines.append(f"#   neighbors_kept_inline={info['neighbors_kept_inline']}")
    if info.get("neighbors_file"):
        lines.append(f"#   neighbors_file={info['neighbors_file']}")
    lines.append("# ====================================")
    lines.append("")
    return lines


def _format_summary(meta: Dict[str, Any]) -> Optional[str]:
    if not meta or meta.get("error"):
        return None
    lines = ["# ==== AUDIO METADATA (probe) ===="]
    path = meta.get("path")
    if path:
        lines.append(f"# source_audio: {path}")
    if meta.get("size_bytes"):
        mb = meta["size_bytes"] / (1024 * 1024)
        lines.append(f"# file_size: {meta['size_bytes']} bytes (~{mb:.2f} MB)")
    ff = meta.get("derived", {}).get("container") or meta.get("ffprobe", {}).get("format") or {}
    stream_sr = ff.get("stream_sample_rate") or ff.get("sample_rate")
    stream_ch = ff.get("stream_channels") or ff.get("channels")
    stream_bits = ff.get("stream_bits_per_sample") or ff.get("bits_per_sample")
    codec = ff.get("stream_codec_name") or ff.get("codec_name")
    bit_rate = ff.get("bit_rate") or ff.get("stream_bit_rate")
    duration = ff.get("duration")
    tag_snippets: list[str] = []
    ff_tags = meta.get("ffprobe", {}).get("format", {}).get("tags") if isinstance(meta.get("ffprobe", {}), dict) else {}
    encoder = None
    itun_norm = None
    itun_smpb = None
    if isinstance(ff_tags, dict):
        encoder = ff_tags.get("encoder") or ff_tags.get("encoding_tool")
        itun_norm = ff_tags.get("iTunNORM")
        itun_smpb = ff_tags.get("iTunSMPB")
        for key, val in ff_tags.items():
            if not isinstance(val, str):
                continue
            shown = val
            if len(shown) > 32:
                shown = shown[:27] + "..."
            tag_snippets.append(f"{key}={shown}")
    mutagen_info = meta.get("tags", {}).get("info") if isinstance(meta.get("tags"), dict) else {}
    if isinstance(mutagen_info, dict):
        encoder = encoder or mutagen_info.get("encoder_info") or mutagen_info.get("encoding_tool")
    mutagen_tags = meta.get("tags", {}).get("tags") if isinstance(meta.get("tags"), dict) else {}
    if isinstance(mutagen_tags, dict):
        itun_norm = itun_norm or mutagen_tags.get("COMM:iTunNORM:eng")
        itun_smpb = itun_smpb or mutagen_tags.get("COMM:iTunSMPB:eng")
    pieces = []
    if codec:
        pieces.append(f"codec={codec}")
    if stream_sr:
        pieces.append(f"sr={stream_sr}")
    if stream_ch:
        pieces.append(f"ch={stream_ch}")
    if stream_bits:
        pieces.append(f"bit_depth={stream_bits}")
    if bit_rate:
        pieces.append(f"bit_rate={bit_rate}")
    if duration:
        pieces.append(f"duration={duration}")
    if tag_snippets:
        pieces.extend(tag_snippets)
    if encoder:
        pieces.append(f"encoder={encoder}")
    if itun_norm:
        pieces.append(f"iTunNORM={str(itun_norm)[:32]}{'...' if len(str(itun_norm))>32 else ''}")
    if itun_smpb:
        pieces.append(f"iTunSMPB={str(itun_smpb)[:32]}{'...' if len(str(itun_smpb))>32 else ''}")
    if pieces:
        lines.append("# container: " + " | ".join(pieces))
    daw = meta.get("derived", {}).get("possible_daw") or []
    if daw:
        labels = [d.get("name") for d in daw if d.get("name")]
        if labels:
            lines.append("# possible_daw: " + ", ".join(labels))
    if len(lines) == 1:
        return None
    lines.append("# ====================================")
    lines.append("")  # trailing newline
    return "\n".join(lines)


def append_metadata(track_dir: Path) -> bool:
    features = _find_single(track_dir.glob("*.features.json"))
    rich = _find_single(track_dir.glob("*.client.rich.txt"))
    if not rich:
        return False
    src = _load_source_audio_from_features(features) if features else None
    if not src:
        src = _load_source_audio_from_rich(rich)
    if not src:
        return False
    neighbor_info = _load_neighbor_meta(features, track_dir) or {}
    meta = extract_audio_metadata(Path(src))
    summary = _format_summary(meta)
    if not summary:
        return False
    # Remove any existing AUDIO METADATA block to avoid duplicates.
    existing = rich.read_text()
    cleaned_lines = []
    in_meta = False
    has_neighbor_block = False
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped == "# ==== AUDIO METADATA (probe) ====":
            in_meta = True
            continue
        if in_meta:
            # End the skip when the next section starts (divider or header).
            if stripped == "# ====================================" or (stripped.startswith("# ===") and "AUDIO METADATA" not in stripped):
                in_meta = False
            continue
        if stripped == "# NEIGHBOR_META:":
            has_neighbor_block = True
        cleaned_lines.append(line)

    summary_lines = summary.rstrip("\n").splitlines()
    if summary_lines and summary_lines[-1].strip():
        summary_lines.append("")
    insert_at: Optional[int] = None
    # Prefer to place audio metadata immediately before AUDIO_PIPELINE (if present)
    for idx, line in enumerate(cleaned_lines):
        if line.strip().startswith("# AUDIO_PIPELINE:"):
            insert_at = max(idx, 0)
            # back up over a preceding blank line to keep grouping tidy
            if insert_at > 0 and cleaned_lines[insert_at - 1].strip() == "":
                insert_at -= 1
            break
    if insert_at is None:
        for idx, line in enumerate(cleaned_lines):
            if "sidecar_health" in line:
                insert_at = idx + 1
                while insert_at < len(cleaned_lines) and cleaned_lines[insert_at].strip() == "":
                    insert_at += 1
                break
    if insert_at is None:
        for idx in range(len(cleaned_lines) - 1):
            if cleaned_lines[idx].strip() == "# ====================================" and cleaned_lines[idx + 1].strip() == "# NEIGHBOR_META:":
                insert_at = idx
                break
    if insert_at is None:
        for idx, line in enumerate(cleaned_lines):
            if line.strip() == "# ==== HISTORICAL ECHO V1 ====":
                insert_at = idx
                break
    if insert_at is None:
        insert_at = len(cleaned_lines)

    neighbor_lines: list[str] = []
    if not has_neighbor_block and neighbor_info:
        neighbor_lines = _format_neighbor_block(neighbor_info)
        if summary_lines and summary_lines[-1].strip() == "# ====================================" and neighbor_lines and neighbor_lines[0].strip() == "# ====================================":
            neighbor_lines = neighbor_lines[1:]

    updated_lines = cleaned_lines[:insert_at] + summary_lines + neighbor_lines + cleaned_lines[insert_at:]
    # If a leftover divider sat before the metadata header, drop it for cleaner layout.
    try:
        meta_idx = updated_lines.index("# ==== AUDIO METADATA (probe) ====")
        if meta_idx > 0 and updated_lines[meta_idx - 1].strip() == "# ====================================":
            del updated_lines[meta_idx - 1]
            if meta_idx - 2 >= 0 and updated_lines[meta_idx - 2].strip() == "":
                del updated_lines[meta_idx - 2]
    except ValueError:
        pass

    # Remove duplicate dividers between metadata and neighbor block if they sit back-to-back.
    try:
        meta_header_idx = updated_lines.index("# ==== AUDIO METADATA (probe) ====")
        meta_divider_idx = None
        for i in range(meta_header_idx, len(updated_lines)):
            if updated_lines[i].strip() == "# ====================================":
                meta_divider_idx = i
                break
        neighbor_idx = updated_lines.index("# NEIGHBOR_META:") if "# NEIGHBOR_META:" in updated_lines else None
        if meta_divider_idx is not None and neighbor_idx is not None:
            neighbor_divider_idx = None
            for j in range(neighbor_idx - 1, -1, -1):
                if updated_lines[j].strip() == "# ====================================":
                    neighbor_divider_idx = j
                    break
            if neighbor_divider_idx is not None and 0 <= neighbor_divider_idx - meta_divider_idx <= 2:
                # Prefer the neighbor divider; drop the metadata divider and any adjacent blank.
                if meta_divider_idx is not None:
                    del updated_lines[meta_divider_idx]
                if neighbor_divider_idx > meta_divider_idx and neighbor_divider_idx < len(updated_lines) and neighbor_divider_idx - 1 >= 0 and updated_lines[neighbor_divider_idx - 1].strip() == "":
                    del updated_lines[neighbor_divider_idx - 1]
    except ValueError:
        pass

    # Between metadata header and NEIGHBOR_META, collapse multiple dividers to one.
    try:
        meta_idx = updated_lines.index("# ==== AUDIO METADATA (probe) ====")
        neighbor_idx = updated_lines.index("# NEIGHBOR_META:")
        divider_positions = [
            i for i in range(meta_idx + 1, neighbor_idx) if updated_lines[i].strip() == "# ===================================="
        ]
        if len(divider_positions) > 1:
            # keep the last divider
            for pos in reversed(divider_positions[:-1]):
                del updated_lines[pos]
        # Remove extra blank lines between metadata and neighbor block.
        while meta_idx + 1 < len(updated_lines) and updated_lines[meta_idx + 1].strip() == "":
            del updated_lines[meta_idx + 1]
    except ValueError:
        pass

    # Ensure a divider immediately precedes NEIGHBOR_META for readability.
    if "# NEIGHBOR_META:" in updated_lines:
        n_idx = updated_lines.index("# NEIGHBOR_META:")
        if n_idx == 0 or updated_lines[n_idx - 1].strip() != "# ====================================":
            updated_lines.insert(n_idx, "# ====================================")

    # Collapse excessive blank lines (keep at most one).
    compacted: list[str] = []
    for line in updated_lines:
        if line.strip() == "" and compacted and compacted[-1].strip() == "":
            continue
        compacted.append(line)

    updated_text = "\n".join(compacted) + "\n"
    rich.write_text(updated_text, encoding="utf-8")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Append audio metadata probe to client.rich.txt")
    p.add_argument("--track-dir", required=True, help="Directory containing *.features.json and *.client.rich.txt")
    args = p.parse_args()
    ok = append_metadata(Path(args.track_dir))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
