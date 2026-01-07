from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import json

def trim_neighbors(echo_data: Dict[str, Any], max_keep: int) -> Dict[str, Any]:
    trimmed = dict(echo_data)
    for key in ("neighbors", "tier1_neighbors", "tier2_neighbors", "tier3_neighbors"):
        if key in trimmed and isinstance(trimmed[key], list):
            trimmed[key] = trimmed[key][:max_keep]
    return trimmed


def _sorted_neighbors(echo_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    neighbors = echo_data.get("neighbors") or []
    return sorted(neighbors, key=lambda n: n.get("distance", float("inf")))


def build_hist_block(echo_data: Dict[str, Any]) -> Dict[str, Any]:
    neighbors = _sorted_neighbors(echo_data)
    decade_counts = echo_data.get("decade_counts") or {}
    primary_decade = None
    if decade_counts:
        primary_decade = sorted(decade_counts.items(), key=lambda x: (-x[1], x[0]))[0][0]
    top_neighbor = neighbors[0] if neighbors else {}
    return {
        "primary_decade": primary_decade,
        "primary_decade_neighbor_count": (decade_counts.get(primary_decade, 0) if primary_decade else 0),
        "top_neighbor": top_neighbor,
        "neighbors": neighbors,
    }


def build_echo_header_line(echo_data: Dict[str, Any]) -> str:
    neighbors = _sorted_neighbors(echo_data)
    decade_counts = echo_data.get("decade_counts") or {}
    if not neighbors:
        return "# ECHO SUMMARY: no_neighbors_found"
    primary_decade = sorted(decade_counts.items(), key=lambda x: (-x[1], x[0]))[0][0] if decade_counts else "unknown"
    count_primary = decade_counts.get(primary_decade, 0)
    tiers_used = sorted({n.get("tier", "tier1_modern") for n in neighbors})
    closest = neighbors[0]
    return (
        "# ECHO SUMMARY: "
        f"tiers={','.join(tiers_used)} | "
        f"primary_decade={primary_decade} ({count_primary}/{len(neighbors)}) | "
        f"closest=({closest.get('tier','')}) {closest.get('year','')} – {closest.get('artist','')} — {closest.get('title','')} "
        f"(dist={closest.get('distance',0):.6f})"
    )


def build_neighbor_lines(echo_data: Dict[str, Any], summary_line: str, max_neighbors: int = 8) -> str:
    """
    Render a rich, human-friendly HISTORICAL ECHO V1 block.
    """
    neighbors_in: List[Dict[str, Any]] = _sorted_neighbors(echo_data)
    padded_neighbors: List[Dict[str, Any]] = neighbors_in[:max_neighbors]

    lines: List[str] = []
    lines.append("# ==== HISTORICAL ECHO V1 ====")
    lines.append(summary_line)
    lines.append("# NEIGHBORS (deduped across tiers; sorted by dist)")
    lines.append("# Legend: tier1=Top40, tier2=Top100, tier3=Top200")
    lines.append("# dist: lower is closer (z-scored Euclidean on tempo/valence/energy/loudness)")
    lines.append("# feature_source: where features came from (e.g., essentia_local, yamaerenay)")
    lines.append("#")
    lines.append("#    #  tier         dist  year  artist                title                           ")
    lines.append("#   ------------------------------------------------------------------------------------")
    for idx, n in enumerate(padded_neighbors[:max_neighbors], start=1):
        lines.append(
            "#   "
            f"{idx:>2}  "
            f"{(n.get('tier','') or ''):10.10} "
            f"{(n.get('distance',0) if n.get('distance') is not None else 0):>6.3f}  "
            f"{(n.get('year','') or ''):>4}  "
            f"{(n.get('artist') or '')[:20]:<20}  "
            f"{(n.get('title') or '')[:32]:<32}"
        )
    lines.append("#")
    # Closest per decade (dynamic buckets), sorted by distance.
    def decade_label(year: int) -> str:
        start = (year // 10) * 10
        return f"{start}\u2013{start+9}"

    best_by_decade: Dict[str, Dict[str, Any]] = {}
    for n in neighbors_in:
        try:
            y = int(n.get("year"))
        except Exception:
            continue
        label = decade_label(y)
        cur = best_by_decade.get(label)
        if cur is None or n.get("distance", float("inf")) < cur.get("distance", float("inf")):
            best_by_decade[label] = n
    if best_by_decade:
        lines.append("# -- Closest snapshots by decade (sorted by dist) --")
        for n in sorted(best_by_decade.values(), key=lambda x: x.get("distance", float("inf"))):
            lines.append(
                "#     "
                f"{(n.get('year','') or ''):>4}  "
                f"{(n.get('artist') or '')[:20]:<20}  "
                f"{(n.get('title') or '')[:32]:<32}  "
                f"dist={(n.get('distance',0) if n.get('distance') is not None else 0):.3f}  "
                f"tier={n.get('tier','')}  "
                f"decade={decade_label(int(n.get('year')))}"
            )
    lines.append("#")
    lines.append("#   ------------------------------------------------------------------------------------")
    return "\n".join(lines)


def write_neighbors_file(path: str, payload: Dict[str, Any], max_neighbors: Optional[int] = None, max_bytes: int = 5 << 20, warnings: Optional[List[str]] = None) -> None:
    data = dict(payload)
    if "neighbors" in data and isinstance(data["neighbors"], list):
        data["neighbors"] = _sorted_neighbors({"neighbors": data["neighbors"]})
        if max_neighbors is not None:
            data["neighbors"] = data["neighbors"][:max_neighbors]
    encoded = json.dumps(data, indent=2)
    if len(encoded.encode("utf-8")) > max_bytes:
        if warnings is not None:
            warnings.append("neighbors_truncated_for_size")
        if "neighbors" in data and isinstance(data["neighbors"], list):
            data["neighbors"] = data["neighbors"][: max(1, max_neighbors or 1)]
        encoded = json.dumps(data, indent=2)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(encoded, encoding="utf-8")


def inject_echo_into_hci(
    hci_data: Dict[str, Any],
    feature_meta: Dict[str, Any],
    echo_data: Dict[str, Any],
    neighbors_out: Path,
    *,
    max_neighbors_inline: int = 4,
) -> Tuple[Dict[str, Any], List[str]]:
    """Return updated HCI payload and warnings; writes neighbors file."""
    warnings: List[str] = []
    sorted_echo = dict(echo_data)
    if "neighbors" in sorted_echo and isinstance(sorted_echo["neighbors"], list):
        sorted_echo["neighbors"] = _sorted_neighbors(sorted_echo)
    try:
        warn_list: List[str] = []
        write_neighbors_file(str(neighbors_out), sorted_echo, max_neighbors=None, max_bytes=5 << 20, warnings=warn_list)
        warnings.extend([f"{neighbors_out.name}:{w}" for w in warn_list])
    except Exception as e:
        warnings.append(f"{neighbors_out.name}:write_error:{e}")

    trimmed_echo = trim_neighbors(sorted_echo, max_keep=max_neighbors_inline)
    hist_block = build_hist_block(trimmed_echo)

    hci_data = dict(hci_data)
    hci_data["historical_echo_v1"] = hist_block
    hci_data["feature_pipeline_meta"] = feature_meta
    hci_data["historical_echo_meta"] = {
        "neighbors_file": str(neighbors_out),
        "neighbors_total": len(echo_data.get("neighbors") or []),
        "neighbor_tiers": sorted({n.get("tier", "tier1_modern") for n in echo_data.get("neighbors") or []}),
        "neighbors_kept_inline": min(max_neighbors_inline, len(echo_data.get("neighbors") or [])),
    }
    return hci_data, warnings


def inject_echo_into_client(
    client_json: Dict[str, Any],
    feature_meta: Optional[Dict[str, Any]],
    hci_meta: Optional[Dict[str, Any]],
    echo_data: Dict[str, Any],
    neighbors_out: Path,
    *,
    max_neighbors_inline: int = 8,
) -> Tuple[Dict[str, Any], List[str], Dict[str, Any]]:
    """Return updated client JSON, warnings, and a header/tail bundle for rendering."""
    warnings: List[str] = []
    sorted_echo = dict(echo_data)
    if "neighbors" in sorted_echo and isinstance(sorted_echo["neighbors"], list):
        sorted_echo["neighbors"] = _sorted_neighbors(sorted_echo)
    try:
        write_neighbors_file(str(neighbors_out), sorted_echo, max_neighbors=None, max_bytes=5 << 20)
    except Exception as e:
        warnings.append(f"{neighbors_out.name}:write_error:{e}")
    trimmed_echo = trim_neighbors(sorted_echo, max_keep=max_neighbors_inline)
    neighbor_total = len(sorted_echo.get("neighbors") or [])
    neighbor_tiers = sorted({n.get("tier", "tier1_modern") for n in sorted_echo.get("neighbors") or []})

    client_json = dict(client_json)
    client_json["historical_echo_meta"] = {
        "neighbors_file": str(neighbors_out),
        "neighbors_total": neighbor_total,
        "neighbor_tiers": neighbor_tiers,
        "neighbors_kept_inline": min(max_neighbors_inline, neighbor_total),
    }
    client_json["historical_echo_v1"] = trimmed_echo
    if feature_meta:
        client_json["feature_pipeline_meta"] = feature_meta

    echo_header_line = build_echo_header_line(sorted_echo)
    neighbor_lines = build_neighbor_lines(trimmed_echo, summary_line=echo_header_line, max_neighbors=max_neighbors_inline)

    neighbors_file_str = str(Path(neighbors_out).resolve())
    bundle = {
        "echo_header_line": echo_header_line,
        "neighbor_lines": neighbor_lines,
        "neighbor_meta_lines": [
            "# NEIGHBOR_META:",
            f"#   neighbors_total={neighbor_total}",
            f"#   neighbor_tiers={neighbor_tiers}",
            f"#   neighbors_kept_inline={min(max_neighbors_inline, neighbor_total)}",
            f"#   neighbors_file={neighbors_file_str}",
        ],
    }
    return client_json, warnings, bundle

__all__ = [
    "build_echo_header_line",
    "build_hist_block",
    "build_neighbor_lines",
    "inject_echo_into_client",
    "inject_echo_into_hci",
    "trim_neighbors",
    "write_neighbors_file",
]
