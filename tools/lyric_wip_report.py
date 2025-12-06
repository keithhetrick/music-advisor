#!/usr/bin/env python3
"""
Human-readable report for a WIP lyric run (LCI/TTC + neighbors).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, Any, List

from ma_lyrics_engine.lci_overlay import load_norms, find_lane, overlay_lci


def resolve_lane_for_overlay(norms: Dict[str, Any], tier: Any, era: str | None, preferred_era: str | None = None) -> Dict[str, Any] | None:
    """
    Pick a reference lane from norms. Prefer explicit lane-era override, otherwise
    try tier+era, then era-only, then first available lane.
    """
    lanes = norms.get("lanes") or []
    if preferred_era:
        for lane in lanes:
            if lane.get("era_bucket") == preferred_era:
                return lane
        return None
    if era:
        for lane in lanes:
            if lane.get("era_bucket") == era and (tier is None or isinstance(tier, str) or lane.get("tier") == tier):
                return lane
        for lane in lanes:
            if lane.get("era_bucket") == era:
                return lane
    return lanes[0] if lanes else None


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_axis_block(axes: Dict[str, Any]) -> List[str]:
    lines = []
    for key in (
        "structure_fit",
        "prosody_ttc_fit",
        "rhyme_texture_fit",
        "diction_style_fit",
        "pov_fit",
        "theme_fit",
    ):
        if key in axes:
            lines.append(f"  - {key}: {axes[key]}")
    return lines


def percentile_from_z(z: float | None) -> str:
    if z is None:
        return "p ~ N/A"
    p = 0.5 * (1.0 + math.erf(z / math.sqrt(2)))
    return f"p ~ {p:.2f}"


def canonical_neighbor_key(nbr: Dict[str, Any]) -> tuple:
    def norm(s):
        if s is None:
            return ""
        return " ".join(str(s).lower().strip().split())
    return (norm(nbr.get("title")), norm(nbr.get("artist")), nbr.get("year"))


def render_report(
    bridge: Dict[str, Any],
    neighbors: Dict[str, Any],
    top_k: int = 10,
    norms: Dict[str, Any] | None = None,
    include_self: bool = False,
    lane_era_filter: str | None = None,
    show_duplicates: bool = False,
) -> str:
    items = bridge.get("items", [])
    if not items:
        return "No items found in bridge payload."
    song = items[0]
    title = song.get("title", "")
    artist = song.get("artist", "")
    year = song.get("year")
    song_id = song.get("song_id")
    tier = song.get("tier") if song.get("tier") is not None else "WIP"
    era = song.get("era_bucket") or "unknown"

    lines: List[str] = []
    lines.append(f"Song: {title} — {artist} (year={year}, song_id={song_id})")
    lines.append(f"Lane: tier={tier}, era_bucket={era}")
    lines.append("---")

    lci = song.get("lyric_confidence_index") or {}
    axes = lci.get("axes") or {}
    lane = lci.get("lane") or {"tier": tier, "era_bucket": era, "profile": lci.get("calibration_profile")}
    overlay = lci.get("overlay")
    lane_for_overlay = None
    if norms:
        lane_for_overlay = resolve_lane_for_overlay(norms, lane.get("tier"), lane.get("era_bucket"), preferred_era=lane_era_filter)
        if overlay is None and lane_for_overlay:
            overlay = overlay_lci(
                song_axes=axes,
                lci_score=lci.get("score"),
                ttc_seconds=(song.get("ttc_profile") or {}).get("ttc_seconds_first_chorus"),
                lane_norms=lane_for_overlay,
            )
    lines.append("")
    lines.append("LCI:")
    if lci.get("score") is not None:
        lines.append(f"  score: {lci.get('score'):.3f}")
    else:
        lines.append("  score: N/A")
    if overlay and overlay.get("lci_score_z") is not None:
        lines.append(f"    ({percentile_from_z(overlay.get('lci_score_z'))})")
    lines.append(f"  raw: {lci.get('raw')}")
    lines.append(f"  calibration_profile: {lci.get('calibration_profile')}")
    if axes:
        lines.append("  Axes:")
        for key in (
            "structure_fit",
            "prosody_ttc_fit",
            "rhyme_texture_fit",
            "diction_style_fit",
            "pov_fit",
            "theme_fit",
        ):
            if key in axes:
                axis_line = f"    - {key}: {axes[key]:.3f}"
                if overlay and overlay.get("axes_z") and overlay["axes_z"].get(key) is not None:
                    axis_line += f" ({percentile_from_z(overlay['axes_z'][key])})"
                lines.append(axis_line)
    if norms and lane_for_overlay is None:
        lines.append("  Overlay: no norms found for selected lane; showing neighbors only.")
    elif lane_for_overlay:
        lines.append(f"Overlay vs lane (era={lane_for_overlay.get('era_bucket')}, profile={norms.get('profile')}):")

    ttc = song.get("ttc_profile") or {}
    lines.append("")
    lines.append("TTC:")
    sec = ttc.get("ttc_seconds_first_chorus")
    bar = ttc.get("ttc_bar_position_first_chorus")
    lines.append(f"  ttc_seconds_first_chorus: {sec if sec is not None else 'N/A'}")
    lines.append(f"  ttc_bar_position_first_chorus: {bar if bar is not None else 'N/A'}")
    lines.append(f"  estimation_method: {ttc.get('estimation_method', 'N/A')}")
    lines.append(f"  profile: {ttc.get('profile', 'N/A')}")
    if ttc.get("ttc_confidence"):
        lines.append(f"  ttc_confidence: {ttc.get('ttc_confidence')}")
    if sec is None and bar is None:
        lines.append("  Note: TTC not found for this WIP (no clear chorus detected).")

    lines.append("")
    lines.append("")
    lines.append("Top neighbors:")
    neighbor_items = neighbors.get("items") or []
    filtered = []
    for nbr in neighbor_items:
        if not include_self and nbr.get("song_id") == song_id:
            continue
        filtered.append(nbr)
    # Dedupe by canonical key unless explicitly showing duplicates
    deduped = []
    seen_keys = set()
    for nbr in filtered:
        key = canonical_neighbor_key(nbr)
        if not show_duplicates:
            if key in seen_keys:
                continue
            seen_keys.add(key)
        deduped.append(nbr)
    if not deduped:
        lines.append("  (none; check features_song_vector coverage or neighbor query filters.)")
    else:
        for idx, nbr in enumerate(deduped[:top_k], start=1):
            title_n = nbr.get("title", "")
            artist_n = nbr.get("artist", "")
            year_n = nbr.get("year")
            sim = nbr.get("similarity")
            tier_n = nbr.get("tier")
            era_n = nbr.get("era_bucket")
            src = nbr.get("source", "")
            lane_str = ""
            if tier_n is not None or era_n:
                lane_str = f", tier={tier_n}, era={era_n}"
            lines.append(
                f"  #{idx} {title_n} — {artist_n} (year={year_n}{lane_str}) [similarity={sim}] {f'[{src}]' if src else ''}".strip()
            )

    # Summary block
    lines.append("")
    lines.append("Summary:")
    strong_axes = []
    dev_axes = []
    axes_percentiles = {}
    if overlay and overlay.get("axes_z"):
        for k, z in overlay["axes_z"].items():
            if z is None:
                continue
            p = 0.5 * (1.0 + math.erf(z / math.sqrt(2)))
            axes_percentiles[k] = p
            if p >= 0.8:
                strong_axes.append(k)
            elif p < 0.4:
                dev_axes.append(k)
    lci_p = None
    if overlay and overlay.get("lci_score_z") is not None:
        lci_p = 0.5 * (1.0 + math.erf(overlay["lci_score_z"] / math.sqrt(2)))
    if lci_p is not None:
        lines.append(f"  - Overall lyric confidence: {lci.get('score'):.2f} (~{lci_p:.2f} lane percentile).")
    if strong_axes:
        lines.append(f"  - Strong axes: {', '.join(strong_axes)}.")
    if dev_axes:
        lines.append(f"  - Development axes: {', '.join(dev_axes)}.")
    ttc_note = ""
    if sec is None and bar is None:
        ttc_note = "No clear chorus detected by v1 heuristic."
    else:
        ttc_note = f"Chorus onset ~{sec}s ({bar} bars) by TTC v1."
    lines.append(f"  - TTC: {ttc_note}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Render a human-friendly report for a WIP lyric run.")
    ap.add_argument("--bridge", required=True, help="Path to *_bridge.json")
    ap.add_argument("--neighbors", required=True, help="Path to *_neighbors.json")
    ap.add_argument("--top-k", type=int, default=10, help="Number of neighbors to display.")
    ap.add_argument("--norms", help="Optional LCI norms JSON to compute overlay if not present in bridge.")
    ap.add_argument("--include-self", action="store_true", help="Include self match in neighbors output.")
    ap.add_argument("--lane-era", help="Optional era_bucket filter for neighbors display (e.g., 2015_2024).")
    ap.add_argument("--limit", type=int, help="Override neighbor display count (fallback to --top-k).")
    ap.add_argument("--show-duplicates", action="store_true", help="Show duplicate neighbors (same title/artist/year).")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    bridge = load_json(Path(args.bridge).expanduser())
    neighbors = load_json(Path(args.neighbors).expanduser())
    norms = load_norms(Path(args.norms)) if args.norms else None
    report = render_report(
        bridge,
        neighbors,
        top_k=args.limit or args.top_k,
        norms=norms,
        include_self=args.include_self,
        lane_era_filter=args.lane_era,
        show_duplicates=args.show_duplicates,
    )
    print(report)


if __name__ == "__main__":
    main()
