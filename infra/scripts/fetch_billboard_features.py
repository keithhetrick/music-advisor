#!/usr/bin/env python3
"""
Fetch audio features for Billboard entries (year-end or weekly) as a stable market source.

Inputs: CSV with at least title, artist, year (optional spotify_id). Example columns:
  year,year_end_rank,title,artist,spotify_id

Behavior:
- For rows with spotify_id, use it directly.
- For rows without spotify_id, search via Spotify (Client Credentials) using title/artist/year.
- Fetch audio features for all resolved IDs.
- Write a features CSV with tempo/runtime/LUFS/energy/danceability/valence, suitable for market_norms snapshot building.

Usage:
  SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... \
  python scripts/fetch_billboard_features.py \
    --input <DATA_ROOT>/billboard/year_end_2024.csv \
    --out <DATA_ROOT>/market_norms/raw/billboard_year_end_2024_features.csv
"""

from __future__ import annotations

import argparse
import csv
import time
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from tools.spotify_client import SpotifyClient, SPOTIFY_API_BASE


def read_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def fetch_audio_features(client: SpotifyClient, track_ids: List[str], access_token: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Fetch audio features. Prefer provided access_token (user token), then fall back to client credentials.
    """
    feats: Dict[str, Dict[str, Any]] = {}
    tokens: List[str] = []
    if access_token:
        tokens.append(access_token)
    try:
        tokens.append(client.get_access_token())
    except Exception:
        pass
    if not tokens:
        raise Exception("No access token available for audio-features.")

    for i in range(0, len(track_ids), 100):
        batch = track_ids[i : i + 100]
        params = {"ids": ",".join(batch)}
        success = False
        for tok in tokens:
            headers = {"Authorization": f"Bearer {tok}"}
            resp = requests.get(f"{SPOTIFY_API_BASE}/audio-features", headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("audio_features", [])
                for item in data:
                    if not item:
                        continue
                    sid = item.get("id")
                    if sid:
                        feats[sid] = item
                success = True
                break
            else:
                print(f"[WARN] audio-features batch {i} status {resp.status_code}: {resp.text} -- trying next token/fallback")
        if not success:
            # fallback per-track with first token
            tok = tokens[0]
            headers = {"Authorization": f"Bearer {tok}"}
            for sid in batch:
                resp_one = requests.get(f"{SPOTIFY_API_BASE}/audio-features/{sid}", headers=headers, timeout=10)
                if resp_one.status_code == 200:
                    item = resp_one.json()
                    if item and item.get("id"):
                        feats[item["id"]] = item
                else:
                    print(f"[WARN] audio-features single {sid} status {resp_one.status_code}: {resp_one.text}")
                time.sleep(0.05)
        time.sleep(0.1)
    return feats


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch Spotify audio features for Billboard entries.")
    ap.add_argument("--input", required=True, help="Billboard CSV (columns: title, artist, year[,spotify_id]).")
    ap.add_argument("--out", required=True, help="Output features CSV.")
    ap.add_argument("--market", default="US", help="Spotify market for search (default US).")
    ap.add_argument("--access-token", default=None, help="Optional user token; otherwise uses client credentials.")
    args = ap.parse_args()

    access_token = args.access_token or os.getenv("SPOTIFY_ACCESS_TOKEN")
    client = SpotifyClient()
    rows = read_rows(Path(args.input))

    resolved: List[Dict[str, Any]] = []
    missing = 0

    for r in rows:
        sid = (r.get("spotify_id") or "").strip()
        title = (r.get("title") or "").strip()
        artist = (r.get("artist") or "").strip()
        year = r.get("year") or r.get("year_end_year") or r.get("release_year")
        year_int = None
        try:
            year_int = int(year) if year else None
        except Exception:
            year_int = None

        if not sid and title and artist:
            try:
                hit = client.search_track(title, artist, year_int, market=args.market)
                if hit:
                    sid = hit["spotify_id"]
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] search failed for {title} / {artist}: {exc}")

        if not sid:
            missing += 1
            continue

        resolved.append(
            {
                "title": title,
                "artist": artist,
                "year": year_int,
                "spotify_id": sid,
            }
        )

    print(f"[INFO] Resolved {len(resolved)} rows; missing {missing}")

    ids = [r["spotify_id"] for r in resolved]
    feats = fetch_audio_features(client, ids, access_token=access_token)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "title",
        "artist",
        "year",
        "spotify_id",
        "tempo_bpm",
        "duration_ms",
        "duration_sec",
        "loudness_LUFS",
        "energy",
        "danceability",
        "valence",
        "popularity",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in resolved:
            frow = dict(r)
            feat = feats.get(r["spotify_id"], {})
            frow.update(
                {
                    "tempo_bpm": feat.get("tempo"),
                    "duration_ms": feat.get("duration_ms"),
                    "duration_sec": feat.get("duration_ms") / 1000.0 if feat.get("duration_ms") else None,
                    "loudness_LUFS": feat.get("loudness"),
                    "energy": feat.get("energy"),
                    "danceability": feat.get("danceability"),
                    "valence": feat.get("valence"),
                    "popularity": feat.get("popularity"),
                }
            )
            writer.writerow(frow)
    print(f"[DONE] Wrote Billboard features CSV -> {out_path}")


if __name__ == "__main__":
    main()
