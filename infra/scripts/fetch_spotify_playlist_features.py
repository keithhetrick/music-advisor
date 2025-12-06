#!/usr/bin/env python3
"""
Fetch audio features for one or more Spotify playlists (proxy for market charts).

Requires SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in env (client credentials flow).

Usage:
  python scripts/fetch_spotify_playlist_features.py \
    --playlists 37i9dQZEVXbLRQDuF5jeBp \
    --out <DATA_ROOT>/market_norms/raw/spotify_US_top50_2025-01.csv

Outputs CSV columns:
  spotify_id,spotify_name,spotify_artist,spotify_album,release_date,popularity,
  tempo_bpm,duration_ms,duration_sec,loudness_LUFS,energy,danceability,valence

Intended as a precursor to `scripts/build_market_norms_snapshot.py`.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from tools.spotify_client import SpotifyClient, SPOTIFY_API_BASE


def _normalize_playlist_id(pid: str) -> str:
    pid = pid.strip()
    if pid.startswith("spotify:playlist:"):
        return pid.split(":")[-1]
    if pid.startswith("https://open.spotify.com/playlist/"):
        return pid.rstrip("/").split("/")[-1].split("?")[0]
    return pid


def fetch_playlist_tracks(
    client: Optional[SpotifyClient],
    playlist_id: str,
    max_tracks: int = 500,
    market: str = "US",
    access_token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    playlist_id = _normalize_playlist_id(playlist_id)
    limit = 100
    offset = 0
    while True:
        url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks"
        params = {"limit": limit, "offset": offset, "market": market}
        if access_token:
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                raise Exception(f"Spotify API error {resp.status_code} for {url}: {resp.text}")
            data = resp.json()
        else:
            if client is None:
                raise Exception("Spotify client not provided and no access_token.")
            data = client._get(url.replace(SPOTIFY_API_BASE, ""), params=params)
        items = data.get("items", [])
        for item in items:
            track = item.get("track") or {}
            if not track or track.get("id") is None:
                continue
            out.append(
                {
                    "spotify_id": track["id"],
                    "spotify_name": track.get("name"),
                    "spotify_artist": ", ".join(a["name"] for a in track.get("artists", [])),
                    "spotify_album": track.get("album", {}).get("name"),
                    "release_date": track.get("album", {}).get("release_date"),
                    "popularity": track.get("popularity"),
                }
            )
        offset += limit
        if len(items) < limit or len(out) >= max_tracks:
            break
    return out[:max_tracks]


def fetch_audio_features(client: SpotifyClient, track_ids: List[str], access_token: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Fetch audio features.
    - Prefer provided access_token (user token), fall back to client credentials if none/failed.
    - If batch fails, fall back to per-track calls and skip failures.
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
        got = False
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
                got = True
                break
            else:
                print(f"[WARN] audio-features batch {i} status {resp.status_code}: {resp.text} -- trying next token/fallback")
        if not got:
            # fall back per track with the first token available
            token = tokens[0]
            headers = {"Authorization": f"Bearer {token}"}
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
    ap = argparse.ArgumentParser(description="Fetch Spotify playlist tracks + audio features to CSV.")
    ap.add_argument("--playlists", required=True, help="Comma-separated Spotify playlist IDs/URLs (e.g., Top 50/Top 200 proxies).")
    ap.add_argument("--out", required=True, help="Output CSV path.")
    ap.add_argument("--max-tracks", type=int, default=500, help="Max tracks per playlist (default 500).")
    ap.add_argument("--market", default="US", help="Spotify market (default US).")
    ap.add_argument("--access-token", default=None, help="Optional user access token (playlist-read scope). If absent, uses client credentials.")
    args = ap.parse_args()

    playlist_access_token = args.access_token or os.getenv("SPOTIFY_ACCESS_TOKEN")
    client = SpotifyClient()
    playlist_ids = [p.strip() for p in args.playlists.split(",") if p.strip()]

    all_tracks: List[Dict[str, Any]] = []
    for pid in playlist_ids:
        print(f"[INFO] Fetching playlist {pid} ...")
        try:
            tracks = fetch_playlist_tracks(client, pid, max_tracks=args.max_tracks, market=args.market, access_token=playlist_access_token)
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] Failed to fetch playlist {pid}: {exc}")
            continue
        all_tracks.extend(tracks)
        print(f"[INFO] Collected {len(tracks)} tracks from playlist {pid}")

    unique_tracks = {t["spotify_id"]: t for t in all_tracks}.values()
    ids = [t["spotify_id"] for t in unique_tracks]
    print(f"[INFO] Fetching audio features for {len(ids)} unique tracks...")
    feats = fetch_audio_features(client, ids, access_token=playlist_access_token)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "spotify_id",
        "spotify_name",
        "spotify_artist",
        "spotify_album",
        "release_date",
        "popularity",
        "tempo_bpm",
        "duration_ms",
        "duration_sec",
        "loudness_LUFS",
        "energy",
        "danceability",
        "valence",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in unique_tracks:
            frow = dict(t)
            feat = feats.get(t["spotify_id"], {})
            frow.update(
                {
                    "tempo_bpm": feat.get("tempo"),
                    "duration_ms": feat.get("duration_ms"),
                    "duration_sec": feat.get("duration_ms") / 1000.0 if feat.get("duration_ms") else None,
                    "loudness_LUFS": feat.get("loudness"),
                    "energy": feat.get("energy"),
                    "danceability": feat.get("danceability"),
                    "valence": feat.get("valence"),
                }
            )
            writer.writerow(frow)
    print(f"[DONE] Wrote features CSV -> {out_path}")


if __name__ == "__main__":
    main()
