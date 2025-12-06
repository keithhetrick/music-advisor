"""
LCI + TTC lane norms builder.
"""
from __future__ import annotations

import json
import sqlite3
import statistics
from typing import Dict, List, Optional

from ma_lyric_engine.lci import CANONICAL_AXES


def collect_records(conn: sqlite3.Connection, profile: Optional[str]) -> List[Dict[str, object]]:
    cur = conn.cursor()
    query = """
    SELECT s.song_id, s.tier, s.era_bucket, l.axis_structure, l.axis_prosody, l.axis_rhyme,
           l.axis_lexical, l.axis_pov, l.axis_theme, l.LCI_lyric_v1_final_score,
           t.ttc_seconds_first_chorus
    FROM features_song_lci l
    JOIN songs s ON s.song_id = l.song_id
    LEFT JOIN features_ttc t ON t.song_id = l.song_id
    """
    params: tuple[object, ...] = ()
    if profile:
        query += " WHERE l.profile=?"
        params = (profile,)
    cur.execute(query, params)
    rows = cur.fetchall()
    records: List[Dict[str, object]] = []
    for row in rows:
        rec = {
            "song_id": row[0],
            "tier": row[1],
            "era_bucket": row[2],
            "axes": {
                "structure_fit": row[3],
                "prosody_ttc_fit": row[4],
                "rhyme_texture_fit": row[5],
                "diction_style_fit": row[6],
                "pov_fit": row[7],
                "theme_fit": row[8],
            },
            "lci_score": row[9],
            "ttc_seconds_first_chorus": row[10],
        }
        if rec["tier"] is None or rec["era_bucket"] is None:
            continue
        records.append(rec)
    return records


def mean_std(vals: List[float]) -> Dict[str, float]:
    if not vals:
        return {"mean": None, "std": None}
    if len(vals) == 1:
        return {"mean": vals[0], "std": 0.0}
    return {"mean": statistics.fmean(vals), "std": statistics.pstdev(vals)}


def build_lane_norms(conn: sqlite3.Connection, profile: Optional[str]) -> Dict[str, object]:
    records = collect_records(conn, profile)
    lanes: Dict[tuple, List[Dict[str, object]]] = {}
    for rec in records:
        key = (profile or rec.get("profile") or "default", rec["tier"], rec["era_bucket"])
        lanes.setdefault(key, []).append(rec)
    lane_entries = []
    for key, recs in lanes.items():
        _, tier, era = key
        axes_keys = CANONICAL_AXES
        axes_stats = {}
        for ax in axes_keys:
            vals = [r["axes"][ax] for r in recs if r["axes"].get(ax) is not None]
            axes_stats[ax] = mean_std(vals)
        lci_stats = mean_std([r["lci_score"] for r in recs if r["lci_score"] is not None])
        ttc_stats = mean_std([r["ttc_seconds_first_chorus"] for r in recs if r.get("ttc_seconds_first_chorus") is not None])
        lane_entries.append(
            {
                "tier": tier,
                "era_bucket": era,
                "count": len(recs),
                "axes_mean": {k: v["mean"] for k, v in axes_stats.items()},
                "axes_std": {k: v["std"] for k, v in axes_stats.items()},
                "lci_score_mean": lci_stats["mean"],
                "lci_score_std": lci_stats["std"],
                "ttc_seconds_mean": ttc_stats["mean"],
                "ttc_seconds_std": ttc_stats["std"],
            }
        )
    return {"profile": profile or "default", "lanes": lane_entries}


def write_lane_norms(conn: sqlite3.Connection, profile: Optional[str], out_path) -> Dict[str, object]:
    norms = build_lane_norms(conn, profile)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(norms, indent=2), encoding="utf-8")
    return norms
