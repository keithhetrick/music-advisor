#!/usr/bin/env python3
"""
spotify_client.py

Small helper for talking to the Spotify Web API using the
Client Credentials flow.

- Reads SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET from environment.
- Retrieves an app-only access token (no user authorization).
- Exposes simple helpers:
    - get_access_token()
    - search_track(title, artist, year, market="US")

IMPORTANT:
  - This is intended for *metadata lookup* only.
  - Spotify's terms prohibit using Spotify content to train ML/AI models.
"""

from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, Optional

import requests


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"


class SpotifyClientError(Exception):
    pass


class SpotifyClient:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None) -> None:
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise SpotifyClientError(
                "Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in environment."
            )

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _request_new_token(self) -> None:
        """
        Obtain a new app-only access token using Client Credentials flow.
        Docs: https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow
        """
        auth_str = f"{self.client_id}:{self.client_secret}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        resp = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data, timeout=10)
        if resp.status_code != 200:
            raise SpotifyClientError(
                f"Failed to obtain access token ({resp.status_code}): {resp.text}"
            )

        payload = resp.json()
        self._access_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        self._token_expires_at = time.time() + expires_in - 60  # refresh 1 min early

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        """
        if self._access_token is None or time.time() >= self._token_expires_at:
            self._request_new_token()
        assert self._access_token is not None
        return self._access_token

    # ------------------------------------------------------------------
    # Core request helper
    # ------------------------------------------------------------------

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an authenticated GET request to the Spotify API.
        """
        token = self.get_access_token()
        url = f"{SPOTIFY_API_BASE}{path}"
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(url, headers=headers, params=params, timeout=10)

        # Handle basic rate limiting gracefully
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            print(f"[WARN] Rate limited by Spotify, sleeping {retry_after} seconds...")
            time.sleep(retry_after)
            # One retry
            resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code != 200:
            raise SpotifyClientError(
                f"Spotify API error {resp.status_code} for {url}: {resp.text}"
            )

        return resp.json()

    # ------------------------------------------------------------------
    # Search helper
    # ------------------------------------------------------------------

    def search_track(
        self,
        title: str,
        artist: str,
        year: Optional[int] = None,
        market: str = "US",
        limit: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a track by title + artist (+ optional year) and return the best match.

        Returns a dict with a subset of fields:
          {
            "spotify_id": ...,
            "spotify_name": ...,
            "spotify_artist": ...,
            "spotify_album": ...,
            "release_date": ...,
            "track_popularity": ...,
          }

        or None if no results are found.
        """
        # Build a query that is reasonably specific but robust to minor title differences
        if year is not None:
            q = f'track:"{title}" artist:"{artist}" year:{year}'
        else:
            q = f'track:"{title}" artist:"{artist}"'

        params = {
            "q": q,
            "type": "track",
            "market": market,
            "limit": limit,
        }

        data = self._get("/search", params=params)
        items = data.get("tracks", {}).get("items", [])
        if not items:
            return None

        # Simple heuristic: choose the highest-popularity result
        best = max(items, key=lambda t: t.get("popularity", 0))

        return {
            "spotify_id": best["id"],
            "spotify_name": best["name"],
            "spotify_artist": ", ".join(a["name"] for a in best["artists"]),
            "spotify_album": best["album"]["name"],
            "release_date": best["album"].get("release_date"),
            "track_popularity": best.get("popularity"),
        }


def main() -> None:
    """
    Quick manual test: run:

        python tools/spotify_client.py "Blinding Lights" "The Weeknd" 2020
    """
    import argparse

    ap = argparse.ArgumentParser(description="Quick Spotify track search test.")
    ap.add_argument("title", help="Track title")
    ap.add_argument("artist", help="Artist name")
    ap.add_argument("year", nargs="?", type=int, help="Release year (optional)")
    args = ap.parse_args()

    client = SpotifyClient()
    result = client.search_track(args.title, args.artist, args.year)

    if not result:
        print("No results found.")
    else:
        print("Best match:")
        for k, v in result.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
