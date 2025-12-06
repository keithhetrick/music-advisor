#!/usr/bin/env python3
"""
acousticbrainz_fetch_for_spine_mbids.py

Fetch a compact subset of AcousticBrainz features for spine recordings with
known MusicBrainz MBIDs. Tier 3 only; optional and non-calibrating.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
import urllib.error
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import glob

from ma_audio_engine.adapters.bootstrap import ensure_repo_root

from tools.db.acousticbrainz_schema import ensure_acousticbrainz_tables
from tools.external.acousticbrainz_utils import extract_compact_features
from tools.spine.spine_slug import make_spine_slug

ensure_repo_root()

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

AB_BASE = "https://acousticbrainz.org/api/v1"

_SSL_CONTEXT: Optional[ssl.SSLContext]
try:
    import certifi  # type: ignore

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _SSL_CONTEXT = None


def parse_tiers_arg(tiers_arg: str | None) -> List[str]:
    if not tiers_arg:
        return list(TIER_SPECS.keys())
    tiers = [t.strip() for t in (tiers_arg or "").split(",") if t.strip()]
    return [t for t in tiers if t in TIER_SPECS]


def load_tier_slugs(conn: sqlite3.Connection, tier: str) -> set[str]:
    spec = TIER_SPECS[tier]
    cur = conn.execute(
        f"""
        SELECT slug, title, artist
        FROM {spec["table"]}
        WHERE echo_tier = ?
        """,
        (spec["echo_tier"],),
    )
    slugs: set[str] = set()
    for slug, title, artist in cur.fetchall():
        slug_val = (slug or "").strip()
        if not slug_val:
            slug_val = make_spine_slug(title or "", artist or "")
        slugs.add(slug_val)
    return slugs


def load_mbid_rows(
    conn: sqlite3.Connection,
    tiers: List[str],
) -> List[Tuple[str, str]]:
    allowed_slugs: set[str] = set()
    for tier in tiers:
        allowed_slugs.update(load_tier_slugs(conn, tier))

    cur = conn.execute(
        "SELECT slug, recording_mbid FROM spine_musicbrainz_map_v1 WHERE recording_mbid IS NOT NULL"
    )
    rows: List[Tuple[str, str]] = []
    for slug, mbid in cur.fetchall():
        if allowed_slugs and slug not in allowed_slugs:
            continue
        rows.append((slug, mbid))
    return rows


def features_exist(conn: sqlite3.Connection, slug: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM features_external_acousticbrainz_v1 WHERE slug = ? LIMIT 1", (slug,)
    )
    return cur.fetchone() is not None


def fetch_json(url: str, user_agent: str) -> Optional[Dict]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"[WARN] HTTP {exc.code} for {url}")
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Fetch failed for {url}: {exc}")
    return None


def fetch_acousticbrainz(mbid: str, user_agent: str) -> Tuple[Optional[Dict], Optional[Dict]]:
    low_url = f"{AB_BASE}/{mbid}/low-level"
    high_url = f"{AB_BASE}/{mbid}/high-level"
    low_json = fetch_json(low_url, user_agent=user_agent)
    high_json = fetch_json(high_url, user_agent=user_agent)
    return low_json, high_json


def save_raw_json(root: Path, mbid: str, suffix: str, payload: Dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    out_path = root / f"{mbid}.{suffix}.json"
    out_path.write_text(json.dumps(payload, indent=2))


def upsert_features(
    conn: sqlite3.Connection,
    slug: str,
    recording_mbid: str,
    compact: Dict[str, Any],
) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO features_external_acousticbrainz_v1 (slug, recording_mbid, features_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            recording_mbid=excluded.recording_mbid,
            features_json=excluded.features_json,
            updated_at=excluded.updated_at
        """,
        (slug, recording_mbid, json.dumps(compact, separators=(",", ":"), sort_keys=True), now, now),
    )
    conn.commit()


def _find_offline_json(base_dir: Path, mbid: str) -> Optional[Dict[str, Any]]:
    """
    Locate an offline JSON payload for an MBID, handling sharded directories.
    Tries direct file, then a recursive glob (<mbid>*.json).
    """
    direct = base_dir / f"{mbid}.json"
    if direct.is_file():
        try:
            return json.loads(direct.read_text())
        except Exception:
            return None

    pattern = str(base_dir / f"**/{mbid}*.json")
    for path_str in glob.iglob(pattern, recursive=True):
        p = Path(path_str)
        if p.is_file():
            try:
                return json.loads(p.read_text())
            except Exception:
                continue
    return None


def _parse_dir_list(arg_val: Optional[str]) -> List[Path]:
    if not arg_val:
        return []
    return [Path(p.strip()) for p in arg_val.split(",") if p.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fetch AcousticBrainz features for spine MBIDs (Tier 3 optional helper)."
    )
    ap.add_argument(
        "--db",
        default="data/historical_echo/historical_echo.db",
        help="SQLite DB path (default: data/historical_echo/historical_echo.db)",
    )
    ap.add_argument(
        "--tiers",
        default="tier3_modern",
        help="Comma list of tiers to include (tier1_modern,tier2_modern,tier3_modern). Default: tier3_modern.",
    )
    ap.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of MBIDs to process.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite existing AcousticBrainz rows.",
    )
    ap.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Delay between API calls (default: 1.0s).",
    )
    ap.add_argument(
        "--user-agent",
        default="music-advisor/0.1 (tier3 acousticbrainz fetch)",
        help="User-Agent header for AcousticBrainz API.",
    )
    ap.add_argument(
        "--raw-dir",
        default="features_external/acousticbrainz",
        help="Directory to store raw AcousticBrainz responses.",
    )
    ap.add_argument(
        "--offline-low-dir",
        default=None,
        help="Optional directory (or comma list of directories) of offline low-level JSON files named <mbid>.lowlevel.json (sharded OK).",
    )
    ap.add_argument(
        "--offline-high-dir",
        default=None,
        help="Optional directory (or comma list of directories) of offline high-level JSON files named <mbid>.highlevel.json (sharded OK).",
    )
    ap.add_argument(
        "--offline-only",
        action="store_true",
        help="Use only offline files if provided; do not hit the AcousticBrainz API.",
    )
    ap.add_argument(
        "--use-sample-dumps",
        action="store_true",
        help="Reserved for offline dumps; no-op for now.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the run without writing to the database.",
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

    mbid_rows = load_mbid_rows(conn, tiers)
    if args.max:
        mbid_rows = mbid_rows[: args.max]

    raw_root = (REPO_ROOT / args.raw_dir) if not Path(args.raw_dir).is_absolute() else Path(args.raw_dir)
    raw_root.mkdir(parents=True, exist_ok=True)

    stats_attempted = 0
    stats_written = 0
    stats_existing = 0
    stats_failed = 0

    offline_low_dirs = _parse_dir_list(args.offline_low_dir)
    offline_high_dirs = _parse_dir_list(args.offline_high_dir)

    for slug, mbid in mbid_rows:
        if not args.force and features_exist(conn, slug):
            stats_existing += 1
            continue

        stats_attempted += 1
        low_json = None
        high_json = None

        # Offline first if provided
        for d in offline_low_dirs:
            low_json = low_json or _find_offline_json(d, f"{mbid}.lowlevel") or _find_offline_json(d, mbid)
            if low_json:
                break
        for d in offline_high_dirs:
            high_json = high_json or _find_offline_json(d, f"{mbid}.highlevel") or _find_offline_json(d, mbid)
            if high_json:
                break

        if not args.offline_only:
            api_low, api_high = fetch_acousticbrainz(mbid, user_agent=args.user_agent)
            # Prefer offline if already loaded; otherwise use API payloads
            low_json = low_json or api_low
            high_json = high_json or api_high
        elif low_json is None and high_json is None:
            # Offline only but no local files found
            print(f"[WARN] No offline files for {mbid}; skipping due to --offline-only")

        if not low_json and not high_json:
            stats_failed += 1
            time.sleep(args.sleep_seconds)
            continue

        compact = extract_compact_features(low_json, high_json)
        if not compact:
            stats_failed += 1
            time.sleep(args.sleep_seconds)
            continue

        print(f"[INFO] {slug} -> {mbid} compact_fields={list(compact.keys())}")
        if not args.dry_run:
            if low_json:
                save_raw_json(raw_root, mbid, "lowlevel", low_json)
            if high_json:
                save_raw_json(raw_root, mbid, "highlevel", high_json)
            upsert_features(conn, slug, mbid, compact)
            stats_written += 1

        time.sleep(args.sleep_seconds)

    print(
        f"[DONE] attempted={stats_attempted} written={stats_written} existing={stats_existing} failed={stats_failed} "
        f"(tiers={','.join(tiers)})"
    )


if __name__ == "__main__":
    main()
