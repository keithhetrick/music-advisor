#!/usr/bin/env python3
"""
spotify_backfill_metadata_from_ids.py

Purpose
-------
Given a core corpus CSV that already has spotify_id values for some
(or all) tracks, backfill the remaining Spotify metadata columns using
the Spotify Web API:

  - spotify_name
  - spotify_artist
  - spotify_album
  - release_date
  - track_popularity

This script is intentionally self-contained:

  * It does NOT import or depend on tools/spotify_client.py.
  * It does NOT change any pipeline behavior automatically.
  * It only runs when you call it explicitly.

Usage
-----

  # 1. Ensure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set in your env.

  cd ~/music-advisor

  python tools/spotify_backfill_metadata_from_ids.py \
    --in  data/core_1600_with_spotify_patched.csv \
    --out data/core_1600_with_spotify_patched_plusmeta.csv

Then, if desired, re-import the plusmeta CSV into historical_echo.db:

  python tools/historical_echo_core_spine_import.py \
    --csv data/private/local_assets/core_spine/core_1600_with_spotify_patched_plusmeta.csv \
    --db  data/private/local_assets/historical_echo/historical_echo.db \
    --reset-core
"""

from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.config.paths import (
    get_core_spine_root,
    get_historical_echo_db_path,
)

import requests


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_TRACK_URL = "https://api.spotify.com/v1/tracks/{track_id}"


def get_env_or_die(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise SystemExit(
            f"[ERROR] Environment variable {name} is required but not set.\n"
            f"        Please export {name}=... before running this script."
        )
    return val


def fetch_access_token(client_id: str, client_secret: str) -> str:
    """
    Use Client Credentials flow to get a short-lived access token.
    """
    data = {"grant_type": "client_credentials"}
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data=data,
        auth=(client_id, client_secret),
        timeout=10,
    )
    if resp.status_code != 200:
        raise SystemExit(
            f"[ERROR] Failed to obtain Spotify access token: "
            f"{resp.status_code} {resp.text}"
        )
    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise SystemExit("[ERROR] No access_token in Spotify token response.")
    return token


def fetch_track_by_id(access_token: str, track_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch track metadata from Spotify using a known track ID.

    Returns:
        dict with track payload on success, or None if not found / error.
    """
    url = SPOTIFY_TRACK_URL.format(track_id=track_id)
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers, timeout=10)

    # Handle 404 or other errors gracefully; just log and return None.
    if resp.status_code == 404:
        print(f"[WARN] Track ID not found on Spotify: {track_id}")
        return None
    if resp.status_code == 429:
        # Rate limiting: respect Retry-After if present
        retry_after = int(resp.headers.get("Retry-After", "2"))
        print(f"[WARN] Rate limited by Spotify, sleeping {retry_after} seconds...")
        time.sleep(retry_after)
        resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code != 200:
        print(
            f"[WARN] Error fetching track ID {track_id}: "
            f"{resp.status_code} {resp.text}"
        )
        return None

    try:
        return resp.json()
    except Exception as e:
        print(f"[WARN] Failed to decode JSON for track ID {track_id}: {e}")
        return None


def load_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise SystemExit(f"[ERROR] Input CSV {path} is empty.")
    return rows


def needs_backfill(row: Dict[str, Any]) -> bool:
    """
    Decide whether this row needs Spotify metadata backfill.

    We consider a row needing backfill if:
      - It has a non-empty spotify_id, and
      - At least one of the key metadata fields is empty / missing.

    We treat '', None, and 'nan' (case-insensitive) as "empty".
    """
    spotify_id = (row.get("spotify_id") or "").strip()
    if not spotify_id:
        return False

    def _empty(val: Any) -> bool:
        if val is None:
            return True
        s = str(val).strip()
        if not s:
            return True
        if s.lower() in {"nan", "none", "null"}:
            return True
        return False

    fields = [
        "spotify_name",
        "spotify_artist",
        "spotify_album",
        "release_date",
        "track_popularity",
    ]
    return any(_empty(row.get(f)) for f in fields)


def backfill_metadata_for_rows(
    rows: List[Dict[str, Any]],
    client_id: str,
    client_secret: str,
) -> List[Dict[str, Any]]:
    """
    For any row that has spotify_id but missing spotify_* metadata,
    call Spotify /v1/tracks/{id} and fill the fields.
    """
    access_token = fetch_access_token(client_id, client_secret)
    updated_count = 0
    attempted = 0

    for idx, row in enumerate(rows, start=1):
        if not needs_backfill(row):
            continue

        spotify_id = (row.get("spotify_id") or "").strip()
        if not spotify_id:
            continue

        attempted += 1
        year = row.get("year", "")
        title = row.get("title", "")
        artist = row.get("artist", "")
        print(
            f"[INFO] Backfilling row {idx}: year={year}, title={title!r}, "
            f"artist={artist!r}, spotify_id={spotify_id}"
        )

        track = fetch_track_by_id(access_token, spotify_id)
        if not track:
            print(f"[WARN] Skipping row {idx}; no track payload for {spotify_id}.")
            continue

        # Extract desired fields from Spotify payload
        try:
            row["spotify_name"] = track.get("name") or row.get("spotify_name")
            # Join multiple artists with ", "
            artists = track.get("artists") or []
            if artists:
                row["spotify_artist"] = ", ".join(a.get("name", "") for a in artists)
            album = track.get("album") or {}
            row["spotify_album"] = album.get("name") or row.get("spotify_album")
            row["release_date"] = album.get("release_date") or row.get("release_date")
            pop = track.get("popularity")
            if pop is not None:
                row["track_popularity"] = str(pop)
            updated_count += 1
        except Exception as e:
            print(
                f"[WARN] Failed to map Spotify fields for row {idx}, "
                f"id={spotify_id}: {e}"
            )

        # Gentle throttle: avoid hammering the API
        time.sleep(0.1)

    print(
        f"[DONE] Attempted backfill for {attempted} row(s) needing metadata; "
        f"successfully updated {updated_count} row(s)."
    )
    return rows


def write_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        raise SystemExit("[ERROR] No rows to write.")

    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[DONE] Wrote backfilled corpus to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill spotify_name/artist/album/release_date/track_popularity "
            "for rows that already have spotify_id."
        )
    )
    parser.add_argument(
        "--in",
        dest="in_csv",
        default=str(get_core_spine_root() / "core_1600_with_spotify_patched.csv"),
        help="Input CSV path (default: core_1600_with_spotify_patched.csv under private/local_assets/core_spine)",
    )
    parser.add_argument(
        "--out",
        dest="out_csv",
        default=str(get_core_spine_root() / "core_1600_with_spotify_patched_plusmeta.csv"),
        help="Output CSV path (default: core_1600_with_spotify_patched_plusmeta.csv under private/local_assets/core_spine)",
    )
    parser.add_argument(
        "--db",
        default=str(get_historical_echo_db_path()),
        help="Optional historical_echo.db (default honors MA_DATA_ROOT).",
    )
    args = parser.parse_args()

    in_path = Path(args.in_csv)
    out_path = Path(args.out_csv)

    if not in_path.exists():
        raise SystemExit(f"[ERROR] Input CSV not found: {in_path}")

    client_id = get_env_or_die("SPOTIFY_CLIENT_ID")
    client_secret = get_env_or_die("SPOTIFY_CLIENT_SECRET")

    rows = load_rows(in_path)
    rows = backfill_metadata_for_rows(rows, client_id, client_secret)
    write_rows(out_path, rows)


if __name__ == "__main__":
    main()
