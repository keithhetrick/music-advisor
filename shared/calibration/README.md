# Calibration Artifacts (US/Pop)

- `market_norms_us_pop.json`: Pinned market norms for US Pop (tempo/runtime/key/mode + loudness). Used by HCI axes and advisory layers; do not change keys without updating consumers. `MARKET_NORMS.loudness_mean/std` should mirror the current loudness norms version.
- `loudness_norms_us_pop_v1.json`: Source-of-truth loudness calibration and provenance (capture profile, offsets, sample cohort). When recomputing, add a new version file (e.g., `*_v2`) and update market norms accordingly; keep old versions for reproducibility.
- `comparisons/`, `packs/`, and other generated artifacts should be documented alongside their creation scripts; keep dated folders for traceability.

## How to regenerate norms (outline)

1. Assemble source audio/features for the target cohort (e.g., US Pop). Keep a manifest of inputs.
2. Run your calibration script/notebook to compute loudness stats and market norms (e.g., tempo/runtime/key/mode distributions). Save outputs with versioned filenames (e.g., `loudness_norms_us_pop_v2.json`, `market_norms_us_pop_v2.json`).
3. Update any downstream configs that read these (HCI axis configs, advisory layers).
4. Commit inputs, scripts, and outputs together so provenance is clear; keep prior versions in place.
