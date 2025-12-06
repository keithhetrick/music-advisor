# Smoke Checklist (host bundle)

Run these after install to confirm the host is healthy:

1) Install (outer venv):  
`pip install --no-build-isolation -e vendor/MusicAdvisor_BuilderPack/builder/export/MusicAdvisor`

2) Local smoke payload:  
`music-advisor-smoke Examples/sample_payload_minimal.json --market 0.48 --emotional 0.67 --round 3`  
Expect: JSON with `HCI_v1`, `Baseline`, `Goldilocks`, `Structural`, `TTC_Gate` populated. HCI_v1 should be non-null (~0.5 for the sample), Baseline should show a profile, and advisory blocks should have content (not empty).

3) QA fixture (in GPT):  
Paste a fixture from `QA/fixtures/*.json` → `/advisor ingest` → `/advisor run full` → `/advisor export summary`.  
Expect: HCI_v1 present; Baseline set; echoes match fixture notes. Drifts >0.05 = investigate.

4) HitCheck summary (optional):  
`/hitcheck init` → `/hitcheck run` → `/hitcheck export summary`  
Expect: neighbors listed, drift table populated, `HCI_v1p` not null. Default config points to a tiny synthetic cohort under `MusicAdvisor/Data/HitCheck_Cohorts/Blueprint_US_Pop_2025_midtempo_v1_1/` for offline smoke; rebuild to use your real cohort.

CLI shortcut: `make hitcheck-smoke` (rebuilds index per config; useful to validate the synthetic cohort is readable).

Common errors & fixes:
- Pack ingest fails: ensure pack JSON has `MARKET_NORMS.profile`, required meta fields, and referenced norms/baselines are present. Run a schema validator if available.
- HCI_v1 null or advisory empty: payload/pack missing axes or TTC/struct fields; use `Examples/sample_payload_minimal.json` as a template.
- Schema validation: if you have schemas under `Schemas/` or `SCHEMAS/`, run your validator against packs/payloads before advisor runs to catch shape drift.
- HitCheck: expect the bundled synthetic cohort to have 2 rows; if `make hitcheck-smoke` reports zero rows/meta mismatch, rebuild the index or check paths.

Fixture/profile cues:
- QA fixtures use MARKET_NORMS.profile `Pop` (see `QA/ExpectedRanges_v1.json` for ranges and norm_version).
- Minimal packs use `US_Pop_2025` in MARKET_NORMS; adjust if your active profile differs.
