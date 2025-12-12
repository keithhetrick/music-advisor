# Historical Echo Delivery (Opt-In CAS Path)

Status: additive/opt-in; default HCI flow remains unchanged.

## Canonical flow

```text
features.json --(hash, probe)--> historical_echo.json
                                   | (sha256, schema validate)
                                   v
                                 manifest.json
                                   |
      write to CAS root (/echo/<config_hash>/<source_hash>/)
```

- `historical_echo.json`: canonicalized JSON (sorted keys) with `schema_id`, `track_id`, `run_id`, `source_hash`, `config_hash`, `db_hash` (optional), `generated_at`, `probe_params`, `feature_pipeline_meta`, `neighbors`, `decade_counts`, `primary_decade`, `top_neighbor`, `neighbor_filter_notes`.
- `manifest.json`: `schema_id`, `artifact.path/sha256/size/etag`, `source_hash`, `config_hash`, `db_hash`, `runner` metadata, optional `signature/lineage`.
- CAS path: `<MA_ECHO_CAS_ROOT>/echo/<config_hash>/<source_hash>/historical_echo.json` (sibling manifest).
- Hash rules: sha256 over canonical JSON (`json.dumps(..., sort_keys=True, separators=(",", ":"))`). ETag == artifact sha256.

## Tooling (additive)

- `tools/hci/historical_echo_runner.py`: CLI/func wrapper that:
  1) loads features JSON,
  2) computes `source_hash`,
  3) runs probe (existing `run_echo_probe_for_features`),
  4) builds canonical payload,
  5) writes `historical_echo.json` + `manifest.json` under CAS.
- `tools/cas_utils.py`: shared helpers for canonical JSON bytes, sha256, and CAS path construction.

## Usage (planned)

```bash
python tools/hci/historical_echo_runner.py \
  --features path/to/track.features.json \
  --out-root data/echo_cas \
  --config-hash auto \
  --db path/to/historical_echo.db \
  --tiers tier1_modern,tier2_modern \
  --top-k 10
```

Outputs live under `data/echo_cas/echo/<config_hash>/<source_hash>/`.

## Compatibility

- Existing Automator/HCI scripts remain the default; CAS is opt-in.
- Consumers should validate `schema_id`, sha256 vs manifest, then cache by ETag.

## Next steps

- Wire optional `--use-cas` flag into `ma_hci_builder.sh` / injectors.
- Add broker/serve helper for immutable URLs + index (“latest”) pointers.
