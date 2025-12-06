# Music Advisor — README

A single-GPT system for **building**, **researching**, and **forecasting** hit potential across genres with clean, modular commands.

## Overview

Music Advisor v1.1 computes HCI_v1 (Historical Echo Index) and provides advisory modules
(Trend, Lyric EI, Optimization Layer). HCI_v1 is the only scoring model.

## Core Flow

/audio import <JSON>
/audio map pack region=<US|...> profile=<US_Pop_2025|...>
/audio finalize → /advisor ingest → /advisor run full
/advisor export summary
/baseline pin <profile_id> | /baseline unpin | /baseline status

## Baseline & Normalization

HCI_v1 logic is unchanged; scores are normalized against a MARKET_NORMS baseline.
When the active baseline refreshes (e.g., US_Pop_2025), runs restandardize. Pin an older
baseline for reproducibility:
/baseline pin US_Pop_2024Q4

### Baseline Profiles (examples)

- US_Pop_2024Q4 (effective 2024-10-31T00:00:00Z)
- US_Pop_2025 (effective 2025-11-01T00:00:00Z)

## Commands

- /audio import
- /audio map pack region=<..> profile=<..>
- /audio finalize → /advisor ingest → /advisor run full
- /advisor export summary
- /baseline pin <profile_id> | /baseline unpin | /baseline status

## Exports

Every advisor export now includes a Baseline block:
{
"Baseline": {
"active_profile": "US_Pop_2025",
"effective_utc": "2025-11-01T00:00:00Z",
"previous_profile": "US_Pop_2024Q4",
"pinned": false,
"note": "HCI_v1 model unchanged; MARKET_NORMS refreshed."
}
}

## Modules (in one GPT)

/cp — Control Panel (build & validate DATA_PACKs)  
/research — Deep Research (press/platform/culture → DATA_PACK)  
/advisor — Trend Advisor (six layers → HCI, prescriptions)  
/dashboard — Validation, comparisons, run history  
/datahub — Save/load DATA_PACKs by ID (in-chat registry)

## Quick Start (new chat)

1. Paste the bootstrap (from your setup notes) into a **brand-new** chat to avoid lag.
2. Upload Knowledge files (this repo’s `SPECS/`, `SCHEMAS/`, `DATA/`, `CHECKLISTS/`, `TEMPLATES/`).
3. Run the smoke test:

````txt
/cp start
/cp edit genre=Country-Rap
/cp edit region=US
/cp finalize
/advisor ingest
/advisor run full
/advisor export summary
  ```

  ## DataPack Schema

- Schema version: **1.2** (see `SCHEMAS/datapack_schema_v1_2.json`)
- MVP (must exist):
`DATA_PACK_META.region`, `DATA_PACK_META.generated_at`,
`MARKET_NORMS.profile`, `MARKET_NORMS.ttc_sec`, `MARKET_NORMS.runtime_sec`,
`MARKET_NORMS.exposures`, `MARKET_NORMS.tempo_band_bpm`.
- Optional fields can be `null`. All nulls are logged as **Known Gaps**.

## Norms Table

Use `DATA/norms_table_2025.json` for default bands (Country-Rap, Pop, Afrobeats, EDM, AC, TikTok teaser).

## Spotify (optional)

- Deploy `ACTIONS/spotify_worker_index.js` to Cloudflare Workers (set `SPOTIFY_CLIENT_ID/SECRET`).
- Update `ACTIONS/spotify_action_openapi.json` with your Worker URL.
- Add the Action in the GPT Builder → Actions.
- Commands (inside GPT):

```txt
/cp spotify search "Artist - Track"
/cp spotify id "SPOTIFY_ID"
````

→ Fills bpm/key/runtime, adds a Spotify `PLATFORM_METRICS` entry, and notes popularity (index).

## Samples

- `SAMPLES/sample_datapack_country_rap_us.json`
- `SAMPLES/sample_datapack_pop_us.json`  
  Use them to test `/advisor ingest → /advisor run full`.

## Versioning

See `VERSIONS.md` for module versions and change notes. Keep **DataPack schema** locked at `1.2` until you explicitly upgrade the schema & validator together.

## House Rules

- Never fabricate numeric metrics. Prefer `null` with a short reason in `notes`.
- Keep outputs concise by default; expand on request.
- On `/cp finalize` print **JSON only** (no extra text).
