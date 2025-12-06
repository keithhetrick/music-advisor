# Music Advisor — Versions & Change Log

## Current Module Versions

| Module          | Version | Status   | Notes                                |
| --------------- | ------- | -------- | ------------------------------------ |
| Control Panel   | v1.3.2  | Active   | Auto-preset, null handling, /help    |
| Trend Advisor   | v1.0    | Active   | Six-layer pipeline + HCI             |
| Deep Research   | v1.0    | Active   | Normalizes press/platform signals    |
| Dashboard       | v1.0    | Active   | Validate, compare, versions, history |
| DataHub         | v0.2    | Active   | In-chat registry (no external DB)    |
| DataPack Schema | **1.2** | Stable   | JSON Schema in SCHEMAS/ (draft-07)   |
| Norms Table     | 2025.1  | Active   | Country-Rap/Pop/Afrobeats/EDM/AC/Any |
| Spotify Action  | 1.0     | Optional | Requires Cloudflare Worker URL       |

## Recent Changes

- **2025-10-29** — Synced Control Panel schema outline to **DataPack 1.2**; added two sample packs; added README & VERSIONS; verified norms alignment.
- **2025-10-22** — Control Panel v1.3.2: auto-preset on genre/region, /help, missing/autofill/assume/strict.
- **2025-10-22** — Unified Router v1.0: merged /cp, /research, /advisor, /dashboard, /datahub into one GPT.
- **2025-10-21** — Spotify Action & Worker (client credentials, search + audio-features).

## 2.6.1 — 2025-10-30

- Added Optimization Layer v1 (config via norms/2025/optimization.json)
- Added Lyric Analysis Layer v1 (/lyrics analyze)
- Updated result_summary_template_v2.txt to include Optimization + Lyric hooks
- Promptsmith Bridge remains embedded in summary
- QA Gauntlet: smoke, presets, snapshots, echo, genre, error tests passed

## 2.6.0 — 2025-10-29

- Router: Autoload TrendSnapshots patch
- Templates: summary v2 with Promptsmith Bridge (initial)
- Norms: 2025 streaming/radio/tiktok baselines

## Upgrade Guidance

- When changing **DataPack schema**, bump the schema file and Control Panel validator in lockstep (e.g., to 1.3). Provide migration notes.
- Keep module version bumps small and documented here; prefer additive changes to avoid breaking existing packs.
