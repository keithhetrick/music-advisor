# Examples

- `sample_payload_minimal.json`: smallest payload for `music-advisor-smoke` (audio_axes + MARKET_NORMS + TTC stub). Expect HCI_v1 plus Baseline/advisory blocks populated.
- `minimal_pack*.json`: compact pack examples for ingest; use with `/advisor ingest` → `/advisor run full`. Expect HCI_v1 present and Baseline set; relative layer strengths vary by pack theme (dance/groove packs should show stronger Sonic/Market, ballad packs stronger Emotional/Cultural).
- `example_datapack_*.json`: fuller DataPack examples covering different sonic profiles (ballad, groove, radio, sync, etc.). Use for richer regression or demo runs; ensure MARKET_NORMS points to your active profile. Expect echoes/advisory notes to align with the theme (e.g., ballad shows slower tempo runtime, sync shows tighter runtime/structure).

Tip: when validating, focus on presence of HCI_v1, Baseline profile, and sensible echoes/advisory notes for the theme; small numeric drift (<0.02) is usually OK, large swings (>0.05) merit investigation.

Checksums: see `Examples/manifest.json` if you want to guard against accidental edits.
