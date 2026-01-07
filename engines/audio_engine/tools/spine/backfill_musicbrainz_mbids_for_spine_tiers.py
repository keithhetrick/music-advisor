#!/usr/bin/env python3
"""
backfill_musicbrainz_mbids_for_spine_tiers.py

Tier 3–only helper to map spine slugs to MusicBrainz recording MBIDs.
Uses lightweight heuristics and keeps existing Tier 1 / Tier 2 semantics untouched.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import ssl
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_historical_echo_db_path

ensure_repo_root()

from tools.db.acousticbrainz_schema import ensure_acousticbrainz_tables
from tools.spine.spine_slug import make_spine_slug, normalize_spine_text

TIER_SPECS = {
    "tier1_modern": {
        "table": "spine_master_v1_lanes",
        "echo_tier": "EchoTier_1_YearEnd_Top40",
    },
    "tier2_modern": {
        "table": "spine_master_tier2_modern_lanes_v1",
        "echo_tier": "EchoTier_2_YearEnd_Top100_Modern",
    },
    "tier3_modern": {
        "table": "spine_master_tier3_modern_lanes_v1",
        "echo_tier": "EchoTier_3_YearEnd_Top200_Modern",
    },
}

MB_BASE = "https://musicbrainz.org/ws/2/recording/"

_SSL_CONTEXT: Optional[ssl.SSLContext]
try:
    import certifi  # type: ignore

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _SSL_CONTEXT = None


@dataclass
class SpineRow:
    slug: str
    title: str
    artist: str
    year: Optional[int]


def _parse_year(raw: str | int | None) -> Optional[int]:
    if raw is None:
        return None
    try:
        return int(str(raw).strip()[:4])
    except ValueError:
        return None


def load_spine_rows(conn: sqlite3.Connection, table: str, echo_tier: str) -> List[SpineRow]:
    """
    Load minimal fields needed for matching. Title/artist are used to build
    slugs when the table does not store one explicitly (Tier 1).
    """
    cur = conn.execute(
        f"""
        SELECT slug, title, artist, year
        FROM {table}
        WHERE echo_tier = ?
        """,
        (echo_tier,),
    )
    rows: List[SpineRow] = []
    for slug, title, artist, year in cur.fetchall():
        slug_val = (slug or "").strip()
        if not slug_val:
            slug_val = make_spine_slug(title or "", artist or "")
        rows.append(
            SpineRow(
                slug=slug_val,
                title=title or "",
                artist=artist or "",
                year=_parse_year(year),
            )
        )
    return rows


def build_query(title: str, artist: str, year: Optional[int]) -> str:
    pieces = []
    if title:
        pieces.append(f'recording:"{title}"')
    if artist:
        pieces.append(f'artist:"{artist}"')
    if year:
        pieces.append(f"date:{year}")
    if not pieces:
        return ""
    return " AND ".join(pieces)


def fetch_musicbrainz_recordings(
    title: str,
    artist: str,
    year: Optional[int],
    user_agent: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    query = build_query(title, artist, year)
    if not query:
        return []
    params = urllib.parse.urlencode({"query": query, "fmt": "json", "limit": str(limit)})
    url = f"{MB_BASE}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("recordings", []) if isinstance(payload, dict) else []


def _parse_artist_credit(rec: Dict[str, Any]) -> str:
    credits = rec.get("artist-credit")
    if not isinstance(credits, list):
        return ""
    names: List[str] = []
    for part in credits:
        if isinstance(part, dict) and "name" in part:
            names.append(str(part["name"]))
    return " & ".join(names)


def _score_candidate(target_slug: str, target_year: Optional[int], rec: Dict[str, Any]) -> Tuple[float, Optional[int]]:
    cand_title = str(rec.get("title") or "")
    cand_artist = _parse_artist_credit(rec)
    cand_slug = make_spine_slug(cand_title, cand_artist)
    slug_match = cand_slug == target_slug

    title_norm = normalize_spine_text(cand_title)
    target_artist_norm, target_title_norm = target_slug.split("__", 1)
    artist_norm = normalize_spine_text(cand_artist)

    score = 0.0
    if slug_match:
        score += 0.65
    elif title_norm and title_norm == normalize_spine_text(target_title_norm):
        score += 0.35

    if artist_norm and artist_norm in target_artist_norm:
        score += 0.25
    elif target_artist_norm in artist_norm:
        score += 0.15

    cand_year: Optional[int] = None
    date_raw = rec.get("first-release-date") or rec.get("date")
    if isinstance(date_raw, str) and date_raw:
        cand_year = _parse_year(date_raw)
    if target_year and cand_year:
        diff = abs(target_year - cand_year)
        if diff <= 1:
            score += 0.1
        elif diff <= 2:
            score += 0.07
        elif diff <= 4:
            score += 0.04

    return min(score, 1.0), cand_year


def pick_best_candidate(
    target_slug: str,
    target_year: Optional[int],
    recordings: Iterable[Dict[str, Any]],
) -> Tuple[Optional[str], float]:
    best_mbid: Optional[str] = None
    best_score = 0.0
    for rec in recordings:
        if not isinstance(rec, dict):
            continue
        mbid = rec.get("id")
        if not mbid:
            continue
        score, _ = _score_candidate(target_slug, target_year, rec)
        if score > best_score:
            best_score = score
            best_mbid = str(mbid)
    return best_mbid, best_score


def upsert_mapping(
    conn: sqlite3.Connection,
    row: SpineRow,
    recording_mbid: str,
    confidence: float,
) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO spine_musicbrainz_map_v1 (slug, title, artist, year, recording_mbid, mbid_confidence, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'musicbrainz_api', ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            title=excluded.title,
            artist=excluded.artist,
            year=excluded.year,
            recording_mbid=excluded.recording_mbid,
            mbid_confidence=excluded.mbid_confidence,
            updated_at=excluded.updated_at
        """,
        (
            row.slug,
            row.title,
            row.artist,
            row.year,
            recording_mbid,
            confidence,
            now,
            now,
        ),
    )
    conn.commit()


def parse_tiers_arg(tiers_arg: str | None) -> List[str]:
    if not tiers_arg:
        return list(TIER_SPECS.keys())
    tiers = [t.strip() for t in (tiers_arg or "").split(",") if t.strip()]
    return [t for t in tiers if t in TIER_SPECS]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Backfill MusicBrainz recording MBIDs for spine tiers (Tier 3 optional helper)."
    )
    ap.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help="SQLite DB path (default honors MA_DATA_ROOT/historical_echo/historical_echo.db).",
    )
    ap.add_argument(
        "--tiers",
        default="tier3_modern",
        help="Comma list of tiers to process (tier1_modern,tier2_modern,tier3_modern). Default: tier3_modern.",
    )
    ap.add_argument(
        "--limit-per-tier",
        type=int,
        default=None,
        help="Optional limit per tier for cautious first runs.",
    )
    ap.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.2,
        help="Delay between MusicBrainz requests (default: 1.2s).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned matches without writing to DB.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-query and overwrite existing MBIDs.",
    )
    ap.add_argument(
        "--user-agent",
        default="music-advisor/0.1 (tier3 mbid backfill)",
        help="User-Agent header for MusicBrainz API.",
    )
    args = ap.parse_args()

    db_path = Path(args.db)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    ensure_acousticbrainz_tables(conn)

    tiers = parse_tiers_arg(args.tiers)
    if not tiers:
        print("[WARN] No valid tiers specified; exiting.")
        return

    cur = conn.execute("SELECT slug, recording_mbid FROM spine_musicbrainz_map_v1")
    existing = {row["slug"]: row["recording_mbid"] for row in cur.fetchall()}

    stats_total = 0
    stats_written = 0
    stats_matched = 0
    stats_missing = 0

    for tier in tiers:
        spec = TIER_SPECS[tier]
        rows = load_spine_rows(conn, spec["table"], spec["echo_tier"])
        if args.limit_per_tier:
            rows = rows[: args.limit_per_tier]
        print(f"[INFO] Tier {tier}: scanning {len(rows)} rows")

        for row in rows:
            stats_total += 1
            if (
                not args.force
                and row.slug in existing
                and existing[row.slug]
            ):
                continue

            try:
                recs = fetch_musicbrainz_recordings(row.title, row.artist, row.year, user_agent=args.user_agent)
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] MusicBrainz lookup failed for {row.slug}: {exc}")
                stats_missing += 1
                time.sleep(args.sleep_seconds)
                continue

            mbid, conf = pick_best_candidate(row.slug, row.year, recs)
            if mbid:
                stats_matched += 1
                print(
                    f"[MATCH] {row.slug} -> {mbid} (conf={conf:.2f}) "
                    f"title='{row.title}' artist='{row.artist}' year={row.year}"
                )
                if not args.dry_run:
                    upsert_mapping(conn, row, mbid, conf)
                    stats_written += 1
            else:
                stats_missing += 1
                print(f"[MISS] {row.slug} title='{row.title}' artist='{row.artist}' year={row.year}")

            time.sleep(args.sleep_seconds)

    print(
        f"[DONE] scanned={stats_total} matched={stats_matched} written={stats_written} missing={stats_missing} "
        f"(tiers={','.join(tiers)})"
    )


if __name__ == "__main__":
    main()
