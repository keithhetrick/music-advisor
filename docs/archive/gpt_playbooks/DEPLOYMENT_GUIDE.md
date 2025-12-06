# Deployment Guide (Custom GPT)

## 1) Create the GPT

- Name: **Music Advisor — Unified**
- Turn **Web Browsing ON** (for /research only). Code Interpreter OFF.

## 2) Upload Knowledge (single ZIP recommended)

Zip **MusicAdvisor/** as **MusicAdvisor_v2.6.0.zip** and upload to Knowledge.

## 3) Instructions

Paste the router + house rules. Keep outputs concise. Ensure DATA_PACK JSONs print with no commentary.

## 4) Conversation Starters

- `/cp start`
- `/cp presets`
- `/cp edit region=US`
- `/cp edit genre=Pop`
- `/cp finalize`
- `/advisor ingest` → `/advisor run full` → `/advisor export summary`

## 5) Boot Self-Test

Ensure `MusicAdvisor_BootSelfTest_v1.txt` is included.  
On new session, it silently verifies core flow then prints:  
**“System ready. Type /help to begin.”**

## 6) QA (optional but recommended)

- Paste a QA fixture from `QA/*.fixture.json`
- Run advisor commands and compare with `QA/ExpectedRanges_v1.json`

## 7) Updating Norms

- Edit `Knowledge/norms/2025/*.json`, bump `norm_version`, update `CHANGELOG.md`.

## Environment & State

- MusicAdvisor/Config/runtime_flags.json controls Trend ON/OFF.
- MusicAdvisor/Config/baseline_state.json persists MARKET_NORMS state:
  - pinned_profile_id (optional)
  - last_used_profile_id
  - previous_profile_id
  - baseline_changed_flag

## Rollouts

- Trend snapshots can change advisory tone (advisory-only).
- MARKET_NORMS baselines auto-refresh quarterly. On refresh, the service emits a one-time banner:
  Baseline update: <profile_id> (effective <timestamp>).
  To freeze behavior for audits: /baseline pin <profile_id>.

Pinning a Baseline
/baseline pin US_Pop_2024Q4
/baseline status
/baseline unpin

CI Checks

- Export must include Baseline.active_profile and Baseline.effective_utc.
- If pinned_profile_id is set, no change banner should appear.
