#!/usr/bin/env python3
"""
Inject a TEMPO LANE OVERLAY (BPM) block into existing .client.rich.txt files without
changing the surrounding layout.

Usage:
  PYTHONPATH=.:engines/audio_engine/src:engines/lyrics_engine/src:src \
  python3 tools/ma_add_tempo_overlay_to_client_rich.py \
    --client-rich "<features_output_root>/.../<song>.client.rich.txt"

Behavior:
- Looks for a sibling <song>.tempo_norms.json in the same directory.
- Builds a compact overlay block and inserts it after the TTC section.
- If the block already exists, the file is left unchanged.
- No other parts of the file are rewritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

ensure_repo_root()


def format_overlay(payload: dict) -> str:
    lane_id = payload.get("lane_id", "unknown")
    lane_stats = payload.get("lane_stats") or {}
    song_bpm = payload.get("song_bpm")
    song_bin = payload.get("song_bin") or {}
    peak_range = lane_stats.get("peak_cluster_bpm_range") or []
    peak_pct = lane_stats.get("peak_cluster_percent_of_lane") or 0.0
    suggested_delta = payload.get("suggested_delta_bpm") or []
    def _fmt(val, digits=1):
        try:
            return f"{float(val):.{digits}f}"
        except Exception:
            return "unknown"
    hit_band = lane_stats.get("hit_medium_percentile_band") or []
    peak_clusters = lane_stats.get("peak_clusters") or []
    shape = lane_stats.get("shape") or {}

    hot_zone = "unknown"
    if isinstance(peak_range, (list, tuple)) and len(peak_range) == 2:
        hot_zone = f"{_fmt(peak_range[0])}–{_fmt(peak_range[1])} BPM"
    delta_line = None
    if isinstance(suggested_delta, (list, tuple)) and len(suggested_delta) == 2:
        try:
            d_lo, d_hi = sorted([float(suggested_delta[0]), float(suggested_delta[1])])
            if d_hi < 0:
                delta_line = f"nudge_to_hit_medium: slow down ~{abs(d_hi):.1f}–{abs(d_lo):.1f} BPM"
            elif d_lo > 0:
                delta_line = f"nudge_to_hit_medium: speed up ~{d_lo:.1f}–{d_hi:.1f} BPM"
            else:
                delta_line = f"nudge_to_hit_medium: -{abs(d_lo):.1f} to +{d_hi:.1f} BPM"
        except Exception:
            delta_line = None
    summary = str(payload.get("advisory_text") or "").replace("\n", " ").strip()
    lines = [
        "# ====================================",
        "# TEMPO LANE OVERLAY (BPM)",
        f"# lane_id: {lane_id}",
        f"# song_bpm: {_fmt(song_bpm)}",
        f"# lane_median_bpm: {_fmt(lane_stats.get('median_bpm'))}",
        f"# lane_hot_zone: {hot_zone}",
        f"# hits_at_song_bpm: {song_bin.get('hit_count', 0)} ({(song_bin.get('percent_of_lane') or 0)*100:.1f}% of lane)",
        f"# lane_hot_zone_share: {peak_pct*100:.1f}% of lane (historical hit medium)",
    ]
    if hit_band and len(hit_band) == 2:
        lines.append(f"# hit_medium_percentile_band: {_fmt(hit_band[0])}–{_fmt(hit_band[1])} BPM (20–80 pct)")
    if peak_clusters:
        top = peak_clusters[0]
        lines.append(
            f"# peak_cluster_primary: {_fmt(top.get('min_bpm'))}–{_fmt(top.get('max_bpm'))} BPM (~{(top.get('weight') or 0)*100:.1f}% lane)"
        )
    if shape:
        lines.append(
            f"# lane_shape: skew={_fmt(shape.get('skew'),2)}, kurtosis={_fmt(shape.get('kurtosis'),2)}, entropy={_fmt(shape.get('entropy'),2)}"
        )
    if delta_line:
        lines.append(f"# {delta_line}")
    lines.extend(
        [
            "#",
            "# SUMMARY:",
            f"# {summary}" if summary else "# summary_unavailable",
            "",
        ]
    )
    return "\n".join(lines)


def inject_overlay(text: str, overlay: str) -> str:
    lines = text.splitlines()

    # Hold the TTC block so we can relocate it after AUDIO_PIPELINE.
    ttc_block: list[str] | None = None
    # Hold the AUDIO METADATA block so we can place it ahead of AUDIO_PIPELINE.
    metadata_block: list[str] | None = None
    # Hold CLIENT PAYLOAD line to relocate and wrap with separators.
    client_payload_block: list[str] | None = None
    # Strip any existing tempo overlay completely.
    cleaned: list[str] = []
    skipping_overlay = False
    i = 0
    while i < len(lines):
        line = lines[i]
        # Drop overlay blocks entirely.
        if "TEMPO LANE OVERLAY (BPM)" in line or (
            line.strip() == "# ====================================" and i + 1 < len(lines) and "TEMPO LANE OVERLAY (BPM)" in lines[i + 1]
        ):
            skipping_overlay = True
            # drop the separator that introduced the overlay
            if cleaned and cleaned[-1].strip() == "# ====================================":
                cleaned.pop()
            i += 1
            continue
        if skipping_overlay and (line.strip().startswith("# ==== AUDIO METADATA") or line.strip().startswith("/audio import") or line.strip().startswith("# AUDIO_PIPELINE:")):
            skipping_overlay = False
        if skipping_overlay:
            i += 1
            continue

        # Capture TTC block (including leading separator) so we can re-place it later.
        if ttc_block is None and line.strip() == "# ====================================" and i + 1 < len(lines) and lines[i + 1].strip() == "# TTC:":
            block: list[str] = [line]
            j = i + 1
            while j < len(lines):
                block.append(lines[j])
                if lines[j].strip() == "" and j + 1 < len(lines) and lines[j + 1].strip().startswith("# ===================================="):
                    # keep the blank line so spacing is preserved
                    break
                if lines[j].strip() == "" and j + 1 < len(lines) and lines[j + 1].strip().startswith("# TEMPO LANE OVERLAY"):
                    break
                if lines[j].strip() == "" and j + 1 < len(lines) and lines[j + 1].strip().startswith("# ==== AUDIO METADATA"):
                    break
                j += 1
            # advance past captured block
            i = j + 1
            ttc_block = block
            continue

        # Capture AUDIO METADATA block to move above AUDIO_PIPELINE.
        if metadata_block is None and line.strip().startswith("# ==== AUDIO METADATA"):
            block: list[str] = [line]
            j = i + 1
            while j < len(lines):
                block.append(lines[j])
                if lines[j].strip() == "" and j + 1 < len(lines) and lines[j + 1].strip().startswith("# AUDIO_PIPELINE:"):
                    break
                j += 1
            metadata_block = block
            i = j + 1
            continue

        # Capture CLIENT PAYLOAD marker to relocate.
        if client_payload_block is None and "CLIENT PAYLOAD" in line:
            client_payload_block = [line]
            i += 1
            continue

        cleaned.append(line)
        i += 1

    # Defaults if TTC or metadata were missing.
    if ttc_block is None:
        ttc_block = [
            "# ====================================",
            "# TTC:",
            "#   ttc_seconds_first_chorus=None",
            "#   ttc_bars_first_chorus=None",
            "#   ttc_source=None",
            "#   ttc_method=None",
            "",
        ]

    out: list[str] = []
    pipeline_block: list[str] | None = None

    i = 0
    while i < len(cleaned):
        line = cleaned[i]

        # Capture AUDIO_PIPELINE block to reattach after metadata.
        if pipeline_block is None and line.strip().startswith("# AUDIO_PIPELINE:"):
            block: list[str] = [line]
            j = i + 1
            while j < len(cleaned):
                # Stop before the next top-level separator.
                if cleaned[j].strip().startswith("# ====================================") and j + 1 < len(cleaned):
                    break
                if cleaned[j].strip().startswith("# NEIGHBOR_META") or cleaned[j].strip().startswith("# ==== HISTORICAL") or cleaned[j].strip().startswith("/audio import"):
                    break
                block.append(cleaned[j])
                j += 1
            # Trim trailing blank lines from the pipeline block.
            while block and not block[-1].strip():
                block.pop()
            pipeline_block = block
            # Advance pointer to the next section start
            while i < len(cleaned):
                if cleaned[i].strip().startswith("# ====================================") or cleaned[i].strip().startswith("# NEIGHBOR_META") or cleaned[i].strip().startswith("# ==== HISTORICAL") or cleaned[i].strip().startswith("/audio import"):
                    break
                i += 1
            continue

        out.append(line)
        i += 1

    # Compose final structure:
    # 1) everything before pipeline (header, HCI interpretation, etc.) is already in `out`
    # 2) metadata block (if found)
    # 3) separator + audio pipeline block
    # 4) TTC block + overlay
    # 5) remaining sections (already in `out` after pipeline removal)
    assembled: list[str] = []

    # Split out prefix (before first top-level separator after interpretation)
    prefix: list[str] = []
    suffix_start = len(out)
    for idx, line in enumerate(out):
        if pipeline_block is None:
            suffix_start = len(out)
            break
        if line.strip().startswith("# ====================================") and idx + 1 < len(out) and (out[idx + 1].strip().startswith("# NEIGHBOR_META") or out[idx + 1].strip().startswith("# ==== HISTORICAL") or out[idx + 1].strip().startswith("/audio import")):
            suffix_start = idx
            break
    prefix = out[:suffix_start]
    suffix = out[suffix_start:]

    assembled.extend(prefix)
    if client_payload_block:
        # Trim trailing blanks/separators before inserting client payload block.
        while assembled and (not assembled[-1].strip() or assembled[-1].strip() == "# ===================================="):
            assembled.pop()
        assembled.append("")
        assembled.append("# ====================================")
        assembled.extend(client_payload_block)
        assembled.append("# ====================================")
    if metadata_block:
        if assembled and assembled[-1].strip():
            assembled.append("")
        assembled.extend(metadata_block)
    if pipeline_block:
        if assembled and assembled[-1].strip():
            assembled.append("")
        assembled.append("# ====================================")
        assembled.extend(pipeline_block)
        # ensure a single blank line before TTC section
        if assembled and assembled[-1].strip():
            assembled.append("")
        else:
            assembled.append("")
        assembled.extend(ttc_block)
        assembled.append(overlay)
    assembled.extend(suffix)

    text_out = "\n".join(assembled)
    # Ensure exactly one blank line before TTC separator.
    text_out = text_out.replace("\n# ====================================\n# TTC:", "\n\n# ====================================\n# TTC:")
    # Collapse any accidental extra blank lines before TTC.
    text_out = text_out.replace("\n\n\n# ====================================\n# TTC:", "\n\n# ====================================\n# TTC:")
    # Collapse double-blank between PHILOSOPHY and HCI INTERPRETATION.
    text_out = text_out.replace("\n\n\n# ==== HCI INTERPRETATION ====", "\n\n# ==== HCI INTERPRETATION ====")
    return text_out


def resolve_sidecar_path(client_path: Path) -> Path:
    """
    Prefer the plain <song>.tempo_norms.json that sits next to the rich file.
    Fallback to the older suffix-based naming (<song>.client.rich.tempo_norms.json).
    """
    parent = client_path.parent
    name = client_path.name
    candidates = []
    # Primary: strip the .client.rich.txt portion, replace with .tempo_norms.json
    if name.endswith(".client.rich.txt"):
        base = name[: -len(".client.rich.txt")]
        candidates.append(parent / f"{base}.tempo_norms.json")
    # Fallback: simple suffix swap on the whole filename
    candidates.append(client_path.with_suffix(".tempo_norms.json"))
    for cand in candidates:
        if cand.exists():
            return cand
    # If nothing exists, return the first candidate so the error message is stable
    return candidates[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject tempo lane overlay into .client.rich.txt without changing layout.")
    ap.add_argument("--client-rich", required=True, help="Path to the .client.rich.txt file to update.")
    args = ap.parse_args()
    client_path = Path(args.client_rich).resolve()
    sidecar_path = resolve_sidecar_path(client_path)
    if not sidecar_path.exists():
        raise SystemExit(f"tempo_norms sidecar not found: {sidecar_path}")
    payload = json.loads(sidecar_path.read_text())
    overlay = format_overlay(payload)
    orig = client_path.read_text()
    updated = inject_overlay(orig, overlay)
    if updated != orig:
        client_path.write_text(updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
