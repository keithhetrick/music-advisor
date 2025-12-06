#!/usr/bin/env python3
import argparse
import csv
import os
import sys
import time
import datetime
from pathlib import Path

from shared.config.paths import get_hci_v2_targets_csv

import requests

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_AUDIO_FEATURES_URL = "https://api.spotify.com/v1/audio-features"


def log(msg: str):
    print(msg, flush=True)


def get_access_token(client_id: str, client_secret: str) -> str:
    log("[INFO] Requesting Spotify access token...")
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=10,
    )
    log(f"[DEBUG] Token response status: {resp.status_code}")
    if resp.status_code != 200:
        log(f"[ERROR] Failed to get access token: {resp.status_code} {resp.text}")
        sys.exit(1)
    data = resp.json()
    return data["access_token"]


def fetch_audio_features_single(token: str, sid: str):
    """
    Fallback: /v1/audio-features/{id}
    """
    url = f"{SPOTIFY_AUDIO_FEATURES_URL}/{sid}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=10)
    log(f"[DEBUG] single audio-features {sid} -> {resp.status_code}")
    if resp.status_code != 200:
        log(f"[WARN] Single audio-features failed for {sid}: "
            f"{resp.status_code} {resp.text}")
        return None
    return resp.json()


def fetch_audio_features_batch(token: str, ids):
    """
    Primary: /v1/audio-features?ids=...
    Fallback: if all items are null, call single endpoint per ID.
    Returns dict spotify_id -> features_dict
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {"ids": ",".join(ids)}
    log(f"[INFO] Calling Spotify audio-features batch for {len(ids)} IDs...")
    resp = requests.get(
        SPOTIFY_AUDIO_FEATURES_URL,
        headers=headers,
        params=params,
        timeout=10,
    )
    log(f"[DEBUG] audio-features batch status: {resp.status_code}")

    if resp.status_code != 200:
        log(f"[ERROR] audio-features batch failed: {resp.status_code} {resp.text}")
        return {}

    data = resp.json()
    items = data.get("audio_features", [])
    non_null = [x for x in items if x]

    log(f"[DEBUG] Batch returned {len(items)} entries, {len(non_null)} non-null")

    out = {}
    # If we actually got non-null feature dicts, use them
    for item in non_null:
        sid = item.get("id")
        if sid:
            out[sid] = item

    # If everything came back null, fall back to per-ID calls
    if not out:
        log("[WARN] Batch returned only null audio_features; "
            "falling back to per-track /audio-features/{id} calls")
        for sid in ids:
            feat = fetch_audio_features_single(token, sid)
            if feat:
                out[sid] = feat
            time.sleep(0.1)

    return out


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Spotify audio features for UT Billboard CSV rows."
    )
    parser.add_argument(
        "--target-csv",
        default=str(get_hci_v2_targets_csv()),
        help="UT Billboard CSV with spotify_id column "
             f"(default: {get_hci_v2_targets_csv()})",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=[1985, 1986],
        help="Years to include (default: 1985 1986)",
    )
    parser.add_argument(
        "--max-rank",
        type=int,
        default=40,
        help="Max year_end_rank to include (default: 40)",
    )
    parser.add_argument(
        "--out-csv",
        default=None,
        help="Exact output CSV path. If omitted, a timestamped file "
             "will be written under --out-dir.",
    )
    parser.add_argument(
        "--out-dir",
        default="calibration/spotify_features",
        help="Base directory for timestamped Spotify features files "
             "(default: calibration/spotify_features)",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=0.3,
        help="Sleep between API batches in seconds (default: 0.3)",
    )
    args = parser.parse_args()

    years = set(args.years)
    target_csv = Path(args.target_csv)

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    log(f"[DEBUG] SPOTIFY_CLIENT_ID set: {bool(client_id)}")
    log(f"[DEBUG] SPOTIFY_CLIENT_SECRET set: {bool(client_secret)}")
    if not client_id or not client_secret:
        log("[ERROR] SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set.")
        sys.exit(1)

    if not target_csv.exists():
        log(f"[ERROR] Target CSV not found: {target_csv}")
        sys.exit(1)

    log(f"[INFO] Loading UT CSV: {target_csv}")
    rows = []
    spotify_ids = set()

    with target_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                year = int(row.get("year", "") or 0)
                rank = int(row.get("year_end_rank", "") or 9999)
            except ValueError:
                continue

            if year not in years or rank > args.max_rank:
                continue

            sid = (row.get("spotify_id") or "").strip()
            if not sid:
                continue

            rows.append(row)
            spotify_ids.add(sid)

    spotify_ids = sorted(spotify_ids)
    log(f"[INFO] Filter result: {len(rows)} UT rows, {len(spotify_ids)} unique spotify_id(s) "
        f"for years={sorted(years)}, max_rank={args.max_rank}")

    if not spotify_ids:
        log("[WARN] No spotify_id values found matching filters. Nothing to do.")
        return

    # Decide output path (timestamped if out-csv not specified)
    years_sorted = sorted(years)
    years_label = (
        f"{years_sorted[0]}_{years_sorted[-1]}"
        if len(years_sorted) > 1
        else str(years_sorted[0])
    )
    if args.out_csv:
        out_csv = Path(args.out_csv)
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(args.out_dir) / years_label
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / f"spotify_audio_features_{years_label}_{timestamp}.csv"

    log(f"[INFO] Using output CSV: {out_csv}")

    token = get_access_token(client_id, client_secret)

    # Fetch in batches of <=100
    features_by_id = {}
    batch_size = 100
    for i in range(0, len(spotify_ids), batch_size):
        batch = spotify_ids[i:i+batch_size]
        log(f"[INFO] Fetching batch {i//batch_size + 1} ({len(batch)} IDs)...")
        batch_feats = fetch_audio_features_batch(token, batch)
        log(f"[INFO] Retrieved {len(batch_feats)} non-null feature records in this step.")
        features_by_id.update(batch_feats)
        time.sleep(args.sleep_sec)

    log(f"[INFO] Total spotify_id(s) with features: {len(features_by_id)}")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "spotify_id",
        "spotify_uri",
        "spotify_href",
        "tempo",
        "key",
        "mode",
        "time_signature",
        "duration_ms",
        "loudness",
        "danceability",
        "energy",
        "valence",
        "acousticness",
        "instrumentalness",
        "liveness",
        "speechiness",
        "year",
        "artist",
        "title",
        "year_end_rank",
    ]

    log(f"[INFO] Writing CSV: {out_csv}")
    count_out = 0
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            sid = (row.get("spotify_id") or "").strip()
            feats = features_by_id.get(sid)

            base = {
                "spotify_id": sid,
                "spotify_uri": feats.get("uri") if feats else "",
                "spotify_href": feats.get("track_href") if feats else "",
                "tempo": feats.get("tempo") if feats else "",
                "key": feats.get("key") if feats else "",
                "mode": feats.get("mode") if feats else "",
                "time_signature": feats.get("time_signature") if feats else "",
                "duration_ms": feats.get("duration_ms") if feats else "",
                "loudness": feats.get("loudness") if feats else "",
                "danceability": feats.get("danceability") if feats else "",
                "energy": feats.get("energy") if feats else "",
                "valence": feats.get("valence") if feats else "",
                "acousticness": feats.get("acousticness") if feats else "",
                "instrumentalness": feats.get("instrumentalness") if feats else "",
                "liveness": feats.get("liveness") if feats else "",
                "speechiness": feats.get("speechiness") if feats else "",
                "year": row.get("year", ""),
                "artist": row.get("artist", ""),
                "title": row.get("title", ""),
                "year_end_rank": row.get("year_end_rank", ""),
            }
            writer.writerow(base)
            count_out += 1

    log(f"[OK] Wrote {count_out} rows to {out_csv}")
    log("[OK] Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"[FATAL] Uncaught exception: {e}")
        raise
