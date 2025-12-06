#!/usr/bin/env python3
"""
acousticbrainz_diagnostics_tier3.py

Coverage + sanity checks for AcousticBrainz Tier 3 staging data.
Console-only; non-calibrating.
"""
from __future__ import annotations

import argparse
import sqlite3
from statistics import mean
from pathlib import Path
from typing import Dict, List, Optional

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

from tools.db.acousticbrainz_schema import ensure_acousticbrainz_tables
from tools.external.acousticbrainz_utils import compact_to_probe_axes, load_compact_from_json
from tools.spine.spine_slug import make_spine_slug

ensure_repo_root()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Diagnostics for AcousticBrainz Tier 3 fallback coverage."
    )
    ap.add_argument(
        "--db",
        default="data/historical_echo/historical_echo.db",
        help="SQLite DB path (default: data/historical_echo/historical_echo.db)",
    )
    ap.add_argument(
        "--echo-tier",
        default="EchoTier_3_YearEnd_Top200_Modern",
        help="Echo tier filter for Tier 3 table.",
    )
    ap.add_argument(
        "--max-compares",
        type=int,
        default=200,
        help="Max rows to include in Essentia vs AcousticBrainz comparison.",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-row comparison details.",
    )
    return ap.parse_args()


def load_tier3_rows(conn: sqlite3.Connection, echo_tier: str) -> List[Dict]:
    cur = conn.execute(
        """
        SELECT slug, title, artist, year, has_audio, audio_features_path,
               tempo, valence, energy, loudness
        FROM spine_master_tier3_modern_lanes_v1
        WHERE echo_tier = ?
        """,
        (echo_tier,),
    )
    rows: List[Dict] = []
    for slug, title, artist, year, has_audio, audio_path, tempo, valence, energy, loudness in cur.fetchall():
        slug_val = (slug or "").strip()
        if not slug_val:
            slug_val = make_spine_slug(title or "", artist or "")

        def _safe_float(v: str | None) -> Optional[float]:
            try:
                if v is None or str(v).strip() == "":
                    return None
                return float(v)
            except ValueError:
                return None

        rows.append(
            {
                "slug": slug_val,
                "has_audio": str(has_audio or "") == "1",
                "audio_features_path": (audio_path or "").strip(),
                "tempo": _safe_float(tempo),
                "valence": _safe_float(valence),
                "energy": _safe_float(energy),
                "loudness": _safe_float(loudness),
            }
        )
    return rows


def load_acousticbrainz(conn: sqlite3.Connection) -> Dict[str, Dict]:
    cur = conn.execute(
        "SELECT slug, features_json FROM features_external_acousticbrainz_v1"
    )
    data: Dict[str, Dict] = {}
    for slug, feat_json in cur.fetchall():
        try:
            compact = load_compact_from_json(feat_json)
            data[slug] = compact
        except Exception:
            continue
    return data


def main() -> None:
    args = parse_args()
    conn = sqlite3.connect(args.db)
    ensure_acousticbrainz_tables(conn)

    tier3_rows = load_tier3_rows(conn, args.echo_tier)
    ab_map = load_acousticbrainz(conn)

    total = len(tier3_rows)
    with_audio = sum(1 for r in tier3_rows if r["has_audio"] and r["audio_features_path"])
    with_ab = sum(1 for r in tier3_rows if r["slug"] in ab_map)
    with_neither = sum(
        1
        for r in tier3_rows
        if not r["audio_features_path"] and r["slug"] not in ab_map
    )

    print("== Tier 3 AcousticBrainz Coverage ==")
    print(f"Total rows: {total}")
    print(f"With Essentia audio_features_path: {with_audio}")
    print(f"With AcousticBrainz compact features: {with_ab}")
    print(f"With neither: {with_neither}")

    overlap_rows = [
        r for r in tier3_rows if r["audio_features_path"] and r["slug"] in ab_map
    ]
    if not overlap_rows:
        print("\nNo rows with both Essentia and AcousticBrainz data; skipping comparison.")
        return

    compares = 0
    tempo_diffs: List[float] = []
    valence_diffs: List[float] = []
    energy_diffs: List[float] = []
    loudness_diffs: List[float] = []

    for r in overlap_rows:
        if compares >= args.max_compares:
            break
        ab_axes = compact_to_probe_axes(ab_map[r["slug"]])
        if not ab_axes:
            continue
        compares += 1
        tempo_diffs.append(abs(ab_axes["tempo"] - (r["tempo"] or 0)))
        valence_diffs.append(abs(ab_axes["valence"] - (r["valence"] or 0)))
        energy_diffs.append(abs(ab_axes["energy"] - (r["energy"] or 0)))
        loudness_diffs.append(abs(ab_axes["loudness"] - (r["loudness"] or 0)))

        if args.verbose:
            print(
                f"[COMPARE] {r['slug']} tempo Δ={tempo_diffs[-1]:.2f} "
                f"valence Δ={valence_diffs[-1]:.3f} energy Δ={energy_diffs[-1]:.3f} "
                f"loudness Δ={loudness_diffs[-1]:.2f}"
            )

    if compares == 0:
        print("\nNo comparable rows with full axis coverage.")
        return

    print("\n== Essentia vs AcousticBrainz (approx axes) ==")
    print(f"Compared rows: {compares} (capped at --max-compares={args.max_compares})")
    print(f"Mean tempo delta:    {mean(tempo_diffs):.2f} bpm")
    print(f"Mean valence delta:  {mean(valence_diffs):.3f}")
    print(f"Mean energy delta:   {mean(energy_diffs):.3f}")
    print(f"Mean loudness delta: {mean(loudness_diffs):.2f} LUFS (approx)")


if __name__ == "__main__":
    main()
