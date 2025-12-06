# Architecture Notes

## Runtime (Chat)

- **Instructions:** Router + House Rules + output discipline.
- **Knowledge:** Norms (2025), era fingerprints, command handlers, boot self-test.
- **State:** `current_pack`, `staged_pack`, `datahub{ id → pack }` kept in conversation.

## Data Model: DATA_PACK (MVP fields)

- `region`, `generated_at`, `MARKET_NORMS.profile`, `ttc_sec`, `runtime_sec`, `exposures`, `tempo_band_bpm`
- Extras: `reference_year`, `reference_eras`, `production_tags[]`, `lyric_motifs[]`, `rhythm_profile`, `tonal_profile{key,mode,energy}`, `Known_Gaps[]`

## Scoring

- **Historical Echo**
  - HEC per era (40/30/20/10): tempo fit, production overlap, rhythm fit, lyric overlap, tonal fit.
  - Historical = 0.50·HEC40 + 0.20·HEC30 + 0.20·HEC20 + 0.10·HEC10
- **HCI** = mean(Historical, Cultural, Market, Emotional, Sonic, Creative)
- Optional: if HEC40 ≥ 0.75 and Market ≥ 0.70 → HCI += 0.02 (cap 1.0)

## Validation (inline)

- bpm: 40–220
- runtime: 30–480s
- ttc: 0–60s
- exposures: 1–10
- Unknowns remain `null` + logged in `Known_Gaps[]`

## Extensibility

- Add `Knowledge/norms/2026/…` and bump `norm_version`.
- Expand `era_fingerprints.json` with new eras (e.g., 1975_disco, 1999_teen_pop).
