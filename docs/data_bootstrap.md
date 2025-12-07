# Data Bootstrap & Layout

This repo keeps `data/` empty by default (git-ignored). To run with real assets, you must populate it. Two options:

1. **Download from your own S3/HTTPS bucket** using the bootstrap script.
2. **Use your own local copies** and point env vars to them.

## Bootstrap via manifest

- Manifest: `infra/scripts/data_manifest.json` (fill real URLs + SHA256 checksums). Dest paths point to `data/public/...` to keep shareable assets separate from private/local-only data.
- Script: `python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`
- Example manifest entry:

  ```json
  {
    "name": "market_norms_us_pop",
    "url": "https://s3.amazonaws.com/your-bucket/market_norms_us_pop.json",
    "sha256": "fill_me",
    "dest": "data/public/market_norms/market_norms_us_pop.json",
    "optional": false
  }
  ```

- Optional entries (e.g., `lyric_intel.db`) can be marked `"optional": true`; failures won’t stop the script.
- The script verifies checksums when provided. Use HTTPS/S3 presigned or public URLs; keep creds out of the repo.

## Data layout (current)

```text
data/
  public/           # shareable/bootstrap assets fetched from S3/HTTPS (manifest allowlist)
    market_norms/
    spine/
    lyric_intel/    # optional
  private/
    local_assets/   # local-only datasets/models (HCI v2 targets/training, core_1600, historical_echo.db, etc.)
    scratch/ experiments/ heavy_internal/  # your personal scratch; never uploaded
  features_output/  # pipeline outputs (generated per run)
```

Private/local_assets quick inventory:

- `hci_v2/` — targets/corpus/training/eval/overlap seeds
- `core_spine/` — core_1600 CSVs, overrides, unmatched
- `historical_echo/` — historical_echo.db and related outputs
- `audio_models/` — trained joblib/meta/calibration for audio/HCI v2
- `yearend_hot100/` — derived year-end aggregates
- `external/` — source datasets (weekly/year_end/lyrics/etc.)
- `lyric_intel/` — lyric DBs/backups/samples (keep private by default)
- `docs/` — local dataset inventories

Current `data/public/` inventory (expected in manifest):

- `market_norms/market_norms_us_pop.json`
- `spine/spine_master.csv`
- `lyric_intel/lyric_intel.db` (optional; only if cleared for distribution)

Lyric Intel DBs default to `data/private/local_assets/lyric_intel/` (kept local). Only add to manifest/S3 if fully cleared.

## Calibration

- Included in repo under `shared/calibration/`. No download required. `MA_CALIBRATION_ROOT` defaults here.

## Path helpers & env overrides

Use `shared.config.paths` (re-exported via `shared.utils.paths`) instead of hard-coded paths. Env overrides:

- `MA_DATA_ROOT` (default: `<repo>/data`)
- `MA_CALIBRATION_ROOT` (default: `<repo>/shared/calibration`)
- `MA_EXTERNAL_DATA_ROOT`, `MA_SPINE_ROOT`, `MA_SPINE_MASTER`, etc.

Override example:

```bash
export MA_DATA_ROOT=/custom/path
python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json
```

## Footprint considerations

- Data is downloaded locally when you run the bootstrap script; nothing is committed.
- If you want zero local DB footprint, you would need to serve datasets via an API and adapt code to stream; current pipelines expect local files under `MA_DATA_ROOT`.

## Quick start

1. Fill `infra/scripts/data_manifest.json` with real URLs/checksums.
2. Run `python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json`.
3. Run `make e2e-app-smoke` or `make quick-check`.

To publish/update public assets to S3 (shareable only):

```bash
BUCKET=music-advisor-data-external-database-resources PREFIX=v1/data/public infra/scripts/data_sync_public.sh
```

This syncs only `data/public/` to the configured bucket/prefix (no delete by default).

## Lyric Intel tempo lanes (tier1/2/3/deep)

The tempo distributions that power `tempo_norms_sidecar` live in `data/private/local_assets/lyric_intel/lyric_intel.db` (table `lane_bpms`, plus matched `features_song.tempo_bpm`). They are built from trusted, private datasets:

- Year-end Top 200 list: `data/private/local_assets/yearend/yearend_hot100_top200_1985_2024.csv`
- Audio features with tempo:
  - `data/private/local_assets/external/audio/hot_100_spotify_audio_features_1958_2021/Hot 100 Audio Features.csv`
  - `data/private/local_assets/external/spotify_dataset_19212020_600k_tracks_yamaerenay/tracks.csv`

Current tiers (after “highest-tier wins” assignment by song):

- `tier1__1985_2025`: 1,093 songs (peak ≤ 40), BPM range ~59–205
- `tier2__1985_2025`: 475 songs (40 < peak ≤ 100), BPM range ~54–206
- `tier3__1985_2025`: 0 songs (no matched tempos for peak 101–200 in the current corpus)
- `deep_echo__1965_1984`: 1,741 songs (1965–1984), BPM range ~54–209
- Total songs with tempo populated: 4,947 of 8,051.
- `tempo_demo.db` is a symlink to this DB.

Rebuild steps (repeatable):

```bash
# 1) Restore the canonical DB backup (kept private/local)
cp data/private/local_assets/lyric_intel/backups/lyric_intel_20251130_161521.db \
   data/private/local_assets/lyric_intel/lyric_intel.db
ln -sfn "$(pwd)/data/private/local_assets/lyric_intel/lyric_intel.db" \
   data/private/local_assets/lyric_intel/tempo_demo.db

# 2) Match tempos to lyric_intel songs (title+artist normalized) from the two feature CSVs
python3 - <<'PY'
import csv, re, sqlite3
from pathlib import Path

def norm(s): return re.sub(r"[^a-z0-9]+","", s.lower())
db = Path("data/private/local_assets/lyric_intel/lyric_intel.db")
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT song_id,title,artist,year,peak_position FROM songs")
li = [(sid,t,a,y,p) for sid,t,a,y,p in cur.fetchall()]
li_map = {norm(f"{t}{a}"): (sid,y,p) for sid,t,a,y,p in li}

sources = [
    Path("data/private/local_assets/external/audio/hot_100_spotify_audio_features_1958_2021/Hot 100 Audio Features.csv"),
    Path("data/private/local_assets/external/spotify_dataset_19212020_600k_tracks_yamaerenay/tracks.csv"),
]
match = {}
for src in sources:
    with src.open() as f:
        r = csv.DictReader(f)
        tempo_cols = [c for c in r.fieldnames or [] if c and ("tempo" in c.lower() or "bpm" in c.lower())]
        title_cols = [c for c in ("Song","title","name") if c in (r.fieldnames or [])]
        artist_cols = [c for c in ("Performer","artist","artists") if c in (r.fieldnames or [])]
        for row in r:
            val = None
            for k in tempo_cols:
                v = row.get(k)
                try:
                    val = float(v); break
                except: pass
            if not val or val <= 0: continue
            t = next((row.get(k) for k in title_cols if row.get(k)), None)
            a = next((row.get(k) for k in artist_cols if row.get(k)), None)
            if not t or not a: continue
            a = re.split(r"[;,]", a)[0].strip()
            key = norm(f"{t}{a}")
            if key in li_map and key not in match:
                match[key] = val

print(f"Matched songs with tempo: {len(match)}")

# 3) Write tempos into features_song and lane_bpms lanes
cur.execute("CREATE TABLE IF NOT EXISTS lane_bpms (lane_id TEXT, bpm REAL)")
cur.execute("UPDATE features_song SET tempo_bpm=NULL")
cur.executemany("UPDATE features_song SET tempo_bpm=? WHERE song_id=?",
                [(v, li_map[k][0]) for k,v in match.items()])

lane_defs = {
    "tier1__1985_2025": lambda y,p: 1985 <= y <= 2025 and p is not None and p <= 40,
    "tier2__1985_2025": lambda y,p: 1985 <= y <= 2025 and p is not None and 40 < p <= 100,
    "tier3__1985_2025": lambda y,p: 1985 <= y <= 2025 and p is not None and 100 < p <= 200,
}
deep_lane = "deep_echo__1965_1984"

cur.execute("DELETE FROM lane_bpms WHERE lane_id LIKE 'tier%' OR lane_id LIKE 'deep_echo%'")

# Highest-tier wins for modern lanes
lane_rows = {k: [] for k in lane_defs}
assigned = set()
for sid, title, artist, year, peak in li:
    if sid in assigned: continue
    if year is None or peak in (None,''): continue
    try: p = float(peak)
    except: continue
    bpm = match.get(norm(f\"{title}{artist}\"))
    if bpm is None: continue
    for lane, pred in lane_defs.items():
        if pred(year, p):
            lane_rows[lane].append(bpm)
            assigned.add(sid)
            break

# Deep echo (era-based, no priority dedupe against modern)
cur.execute(\"\"\"SELECT f.tempo_bpm FROM songs s JOIN features_song f ON s.song_id=f.song_id
              WHERE f.tempo_bpm IS NOT NULL AND f.tempo_bpm>0 AND s.year BETWEEN 1965 AND 1984\"\"\")
deep_bpms = [row[0] for row in cur.fetchall()]

for lane, bpms in lane_rows.items():
    cur.executemany(\"INSERT INTO lane_bpms(lane_id,bpm) VALUES (?,?)\", [(lane,b) for b in bpms])
cur.executemany(\"INSERT INTO lane_bpms(lane_id,bpm) VALUES (?,?)\", [(deep_lane,b) for b in deep_bpms])
conn.commit()

for lane in list(lane_defs)+[deep_lane]:
    cur.execute(\"SELECT COUNT(*), MIN(bpm), MAX(bpm) FROM lane_bpms WHERE lane_id=?\", (lane,))
    print(lane, cur.fetchone())
conn.close()
PY
```

This script:

- Restores the backup DB.
- Matches tempos from the two external feature CSVs to lyric_intel songs (title+artist normalization).
- Fills `features_song.tempo_bpm` for matched songs.
- Populates lanes with “highest-tier wins”: tier1 (peak ≤ 40), tier2 (40–100), tier3 (100–200), deep_echo (1965–1984). Songs only appear in their highest applicable tier; deep is era-based.
- Leaves tier3 empty if no matched tempos exist for peak 101–200 in the current corpus.

If you want to revert to synthetic or broader pools, rerun with different lane definitions and/or sources. Keep `lyric_intel.db` private; do not commit or publish without clearance.
