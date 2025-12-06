#!/usr/bin/env python3
from __future__ import annotations

"""
hci_report_scores.py

Utility to print a quick leaderboard-style report over .hci.json files.

For each track, we try to show:

- role                -> benchmark | wip
- HCI_v1_final_score  -> what the app should display
- HCI_v1_final_tier   -> human-readable tier label
- HCI_audio_v2.score  -> calibrated v2 audio score (if present)
- audio_name          -> friendly track label (fallback: stem of path)

Typical usage:

  # Top 15 benchmark anchors from the 100-song cohort
  python tools/hci_report_scores.py \
    --root features_output/2025/11/17 \
    --role benchmark \
    --top-k 15

  # All WIPs for a given day
  python tools/hci_report_scores.py \
    --root features_output/2025/11/18 \
    --role wip \
    --top-k 100
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class HciRow:
    path: Path
    role: str
    final_score: float
    final_tier: str
    audio_v2_score: Optional[float]
    audio_name: str
    year: Optional[int]


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _infer_year_from_path(path: Path) -> Optional[int]:
    """
    Try to infer a 4-digit year from the slug directory
    (e.g. '2023_miley_cyrus__flowers__album').
    Best-effort; if we can't, return None.
    """
    try:
        slug_dir = path.parent.name
        # e.g. '2023_miley_cyrus__flowers__album' -> '2023'
        prefix = slug_dir.split("_", 1)[0]
        if prefix.isdigit() and len(prefix) == 4:
            return int(prefix)
    except Exception:
        pass
    return None


def _collect_rows(root: Path, role_filter: str) -> List[HciRow]:
    rows: List[HciRow] = []

    for hci_path in sorted(root.rglob("*.hci.json")):
        try:
            hci = _load_json(hci_path)
        except Exception as exc:
            print(f"[WARN] Could not read {hci_path}: {exc}")
            continue

        role = hci.get("HCI_v1_role") or "wip"
        if role_filter != "any" and role != role_filter:
            continue

        final_score = hci.get("HCI_v1_final_score")
        if final_score is None:
            # If there's no final yet, skip; that means pipeline didn't run fully.
            continue

        final_tier = hci.get("HCI_v1_final_tier") or ""

        audio_v2_score = None
        hci_audio_v2 = hci.get("HCI_audio_v2")
        if isinstance(hci_audio_v2, dict):
            audio_v2_score = hci_audio_v2.get("score")

        audio_name = hci.get("audio_name") or hci_path.stem
        year = _infer_year_from_path(hci_path)

        rows.append(
            HciRow(
                path=hci_path,
                role=role,
                final_score=float(final_score),
                final_tier=str(final_tier),
                audio_v2_score=float(audio_v2_score) if audio_v2_score is not None else None,
                audio_name=str(audio_name),
                year=year,
            )
        )

    return rows


def _print_table(rows: List[HciRow], title: str, sort_by: str, top_k: int) -> None:
    if not rows:
        print(f"[INFO] No rows to display for {title}")
        return

    # Sort
    if sort_by == "audio_v2":
        rows.sort(
            key=lambda r: (r.audio_v2_score if r.audio_v2_score is not None else -1.0),
            reverse=True,
        )
    else:
        rows.sort(key=lambda r: r.final_score, reverse=True)

    if top_k > 0:
        rows = rows[:top_k]

    # Column widths
    rank_width = 3
    score_width = 5
    v2_width = 5
    year_width = 4
    role_width = max(len("role"), max(len(r.role) for r in rows))
    tier_width = max(len("tier"), min(40, max(len(r.final_tier) for r in rows)))
    name_width = min(60, max(len(r.audio_name) for r in rows))

    header = (
        f"{' #':>{rank_width}}  "
        f"{'final':>{score_width}}  "
        f"{'v2':>{v2_width}}  "
        f"{'year':>{year_width}}  "
        f"{'role':<{role_width}}  "
        f"{'tier':<{tier_width}}  "
        f"{'audio_name':<{name_width}}"
    )

    print("")
    print("=" * len(header))
    print(title)
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for idx, row in enumerate(rows, start=1):
        v2_str = (
            f"{row.audio_v2_score:.3f}" if row.audio_v2_score is not None else "  -  "
        )
        year_str = f"{row.year}" if row.year is not None else "    "
        tier_short = row.final_tier
        if len(tier_short) > tier_width:
            tier_short = tier_short[: tier_width - 1] + "…"

        name_short = row.audio_name
        if len(name_short) > name_width:
            name_short = name_short[: name_width - 1] + "…"

        line = (
            f"{idx:>{rank_width}}  "
            f"{row.final_score:>{score_width}.3f}  "
            f"{v2_str:>{v2_width}}  "
            f"{year_str:>{year_width}}  "
            f"{row.role:<{role_width}}  "
            f"{tier_short:<{tier_width}}  "
            f"{name_short:<{name_width}}"
        )
        print(line)

    print("")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Report HCI_v1_final_score and HCI_audio_v2.score over .hci.json files."
    )
    ap.add_argument(
        "--root",
        action="append",
        required=True,
        help="Root directory (can be given multiple times). "
        "All *.hci.json files under each root will be scanned.",
    )
    ap.add_argument(
        "--role",
        choices=["benchmark", "wip", "any"],
        default="any",
        help="Filter by HCI_v1_role (default: any).",
    )
    ap.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Show top K rows by final score (0 = show all, default: 20).",
    )
    ap.add_argument(
        "--sort-by",
        choices=["final", "audio_v2"],
        default="final",
        help="Sort by final score or audio_v2 score (default: final).",
    )

    args = ap.parse_args()

    all_rows: List[HciRow] = []
    for root_str in args.root:
        root = Path(root_str).expanduser().resolve()
        if not root.exists():
            print(f"[WARN] Root does not exist, skipping: {root}")
            continue
        rows = _collect_rows(root, role_filter=args.role)
        all_rows.extend(rows)

    if not all_rows:
        print("[INFO] No matching .hci.json rows found.")
        return

    lbl = f"role={args.role}, sort_by={args.sort_by}, roots={', '.join(args.root)}"
    _print_table(all_rows, title=f"HCI report ({lbl})", sort_by=args.sort_by, top_k=args.top_k)


if __name__ == "__main__":
    main()
