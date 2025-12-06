# Music Advisor — QA Fixtures (Regression Packs)

Use these packs (see `QA/fixtures/*.json`) to quickly verify routing, norms binding, Historical Echo, and HCI stability after any update.

## How to run (in chat)

1. Paste one fixture JSON block.
2. `/advisor ingest`
3. `/advisor run full`
4. `/advisor export summary`
5. Optionally: `/dashboard validate` and `/datahub save "<label>"`

Directional read (what “good” looks like)
- `/advisor ingest` should ACK with no missing-field errors.
- `/advisor run full` should return HCI_v1 plus 6 advisory layers; no layer should be null.
- `/advisor export summary` should show Baseline info (profile/effective date) and populated Market/Sonic/Cultural notes.
- Relative ordering matters more than exact decimals; compare against prior runs.

## What to expect

- MVP fields present and in-range.
- Historical Echo:
  - US Pop fixture: strong 1985 correlation (HEC_40 high).
  - Global K-Pop fixture: strong modern dance/pop alignment, secondary echoes.
  - LATAM Urban fixture: mid-tempo, rhythmic emphasis, contemporary motifs.
- HCI and 6 layers returned. For regression, look for consistent ballpark scores (relative ranking more important than exact decimals).
- If HCI is `null` or layers missing, the ingest failed—check schema and MARKET_NORMS binding.

Pass / watch / fail cues
- Pass: HCI_v1 present; Baseline profile matches fixture expectation; layers populated; echoes align with fixture notes above.
- Watch: Minor score drift (<0.02) vs last known good; investigate recent baseline or norms changes.
- Fail: HCI_v1 null; layers missing; Baseline missing; Historical Echo bands empty/mismatched to fixture; large score swings (>0.05) without intentional changes.

Approximate bands (guidance, not hard thresholds)
- US Pop fixture: HCI_v1 ≈ mid-0.4s to low-0.5s; strong HEC_40.
- Global K-Pop fixture: HCI_v1 ≈ high-0.3s to mid-0.4s; echoes skew modern.
- LATAM Urban fixture: HCI_v1 ≈ mid-0.3s; rhythm/dance layers healthy.

For numeric layer ranges, see `QA/ExpectedRanges_v1.json`. If a layer drifts >0.05 outside its range, review recent baseline/norm/router changes.

Common errors & fixes
- Baseline missing in summary: ensure MARKET_NORMS.profile is set and baseline files are present (or fetched).
- HCI_v1 null: payload missing axes or failed ingest → check fixture fields.
- Echo bands empty/misaligned: norms/router files missing or mismatched profile → verify file placement and manifest.

Fixture → profile/norms
- US_Pop.fixture.json → MARKET_NORMS.profile `Pop`, norm_version 2025.1 (see ExpectedRanges).
- Global_KPop.fixture.json → profile `Pop` (router handles cultural layer); norm_version 2025.1.
- LATAM_Urban.fixture.json → profile `Pop`, norm_version 2025.1.

## Version

- router_version: v2.6.0
- norm_version: 2025.1
