# Config Profiles

This repo now follows a single pattern for selecting config/calibration payloads:

- Default profile string baked into code.
- Env var override (e.g., `LYRIC_LCI_PROFILE`, `LYRIC_LCI_CALIBRATION`, `LYRIC_TTC_PROFILE`, `LYRIC_TTC_CONFIG`).
- CLI flag override when available (highest precedence).
- Profile label can also come from the JSON itself (`calibration_profile` or `profile`) when no override is present.

Use `ma_config.profiles.resolve_profile_config` to apply this precedence and load JSON once in the loader/sidecar. Engines remain pure and receive already-parsed dicts.

## Why profiles exist

- Keep tuned parameters (time bounds, QA thresholds, neighbor settings) in one place so swaps are config changes, not code changes.
- Ensure pipeline driver, HCI builder, host/chat, and neighbors stay consistent by sharing labels and resolvers.

Profile Naming (examples)

- Lyric LCI: `lci_us_pop_v1` (calibration/lci_calibration_us_pop_v1.json)
- Lyric TTC: `ttc_us_pop_v1` (calibration/ttc_profile_us_pop_v1.json)
- Audio HCI: `hci_calibration_us_pop_v1`, `hci_audio_v2_calibration_pop_us_2025Q4` (calibration/\*.json)
- Market/norms: `market_norms_us_pop.json`, `loudness_norms_us_pop_v1.json`

Current Config Surfaces (inventory)

- Lyric LCI calibration: `calibration/lci_calibration_us_pop_v1.json` (axis mu/sigma/clip/weights + component_weights), used by `ma_lyric_engine.lci`.
- LCI lane norms output: built via `ma_lyric_engine.lci_norms.build_lane_norms` / `write_lane_norms`, read by `ma_lyric_engine.export` and `ma_lyric_engine.lci_overlay`.
- LCI overlay norms path env: `LYRIC_LCI_NORMS_PATH` in `ma_lyric_engine.export`.
- TTC heuristics: `calibration/ttc_profile_us_pop_v1.json` (seconds_per_section_fallback, beats_per_bar); loader in `tools/ttc_sidecar.py`.
- Audio/HCI calibration + policies: `calibration/hci_calibration_us_pop_v1.json`, `hci_audio_v2_calibration_pop_us_2025Q4.json`, `hci_policy_v1.json`, market norms JSONs.
- Loudness/market norms: `calibration/loudness_norms_us_pop_v1.json`, `calibration/market_norms_us_pop*.json`.
- Historical echo/neighbor configs: present under `calibration/` and `config/` (e.g., policy and norms files); still hard-coded defaults in CLI helpers.

ma_config helpers (new)

- Paths: `ma_config.paths.get_data_root()`, `get_calibration_root()`, `get_lyric_intel_db_path()` honor `MA_DATA_ROOT`/`MA_CALIBRATION_ROOT`.
- Profiles: `ma_config.profiles.resolve_profile_config` centralizes CLI/env/default resolution; default constants live alongside calibration files.
- Audio: `ma_config.audio` provides `resolve_hci_calibration`, `resolve_market_norms`, `resolve_audio_policy` with env overrides (`AUDIO_HCI_PROFILE`, `AUDIO_HCI_CALIBRATION`, `AUDIO_MARKET_NORMS`, `AUDIO_HCI_POLICY`) and defaults to calibration JSONs.
- Neighbors: `ma_config.neighbors.resolve_neighbors_config` handles `limit`/`distance` via CLI/env (`LYRIC_NEIGHBORS_LIMIT`, `LYRIC_NEIGHBORS_DISTANCE`).
- Constants: `ma_config.constants` centralizes LCI axis names, era buckets, tier thresholds so lane helpers stay data-driven.
- Audio v2 calibration: `resolve_audio_v2_calibration` (env `AUDIO_HCI_V2_CALIBRATION`, default `calibration/hci_audio_v2_calibration_pop_us_2025Q4.json`).
- Audio v2 datasets: `resolve_hci_v2_targets`, `resolve_hci_v2_corpus`, `resolve_hci_v2_training_out` with env overrides `HCI_V2_TARGETS_CSV`, `HCI_V2_CORPUS_CSV`, `HCI_V2_TRAINING_CSV` (defaults under `data/`).
- Norms schema: `docs/schemas/market_norms.schema.json`.

Sidecar/CLI Expectations

- Lyric STT sidecar (`tools/lyric_stt_sidecar.py`):
  - Env: `LYRIC_LCI_PROFILE`, `LYRIC_LCI_CALIBRATION`, `LYRIC_LCI_NORMS_PATH`.
  - CLI: `--lci-profile`, `--lci-calibration` (optional; CLI wins over env).
- TTC sidecar (`tools/ttc_sidecar.py`):
  - Env: `LYRIC_TTC_PROFILE`, `LYRIC_TTC_CONFIG`.
  - CLI: `--ttc-profile` (label or legacy path), `--ttc-config` JSON path, `--seconds-per-section` fallback.
- Engines (`ma_lyric_engine`, `ma_ttc_engine`, `ma_audio_*`): accept config dicts; filesystem/env handling should live in loaders.

## Quick reference: precedence

| Source              | Precedence                        |
| ------------------- | --------------------------------- |
| CLI flag            | Highest                           |
| Env var             | Middle                            |
| Default profile     | Lowest                            |
| JSON-embedded label | Used when no override is provided |

Pending Hard-Coded Values To Externalize

- TTC detection fallback seconds-per-section and beats-per-bar defaults are still defined in code but now read from TTC profile when provided.
- Audio HCI axis definitions, weights, and market norms live in calibration JSONs but many scripts still carry defaults inline; these should be routed through the shared profile resolver next.
