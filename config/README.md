# Config overrides (optional)

Drop these JSON files in `config/` to change behavior without code edits:

- `backend_registry.json` — override supported sidecar backends and default sidecar command.
  - Optional: `"enabled_backends": {"essentia": true, "madmom": true, "librosa": true, "auto": true}`
  - Optional per-backend settings: `"backends": {"essentia": {"tempo_confidence_bounds": [0.93, 3.63]}}`
  - Contract: sidecars should emit a small JSON object (≤5MB) with backend/meta + payload (see `docs/sidecar_tempo_key.md` for tempo sidecar fields).
- `tempo_confidence_bounds.json` — override per-backend tempo confidence bounds/labels.
- `qa_policy.json` — override QA thresholds per policy name.
- `logging.json` — set default log prefix/redaction/secrets. Optional sandbox block:
  ```json
  {
    "sandbox": {
      "enabled": false,
      "drop_beats": false,
      "drop_neighbors": false,
      "max_chars": null
    }
  }
  ```
  When `enabled` is true (or `LOG_SANDBOX=1`), beat grids/neighbors are stripped from outputs and long strings truncated (safe sharing/diagnostics).
- `cache.json` — set `default_cache_dir` and `default_backend` (`disk` or `noop`).
- `hash.json` — set `algorithm` (e.g., `sha256`, `blake2b`) and `chunk_size`.

All files are optional; absent files keep defaults. Invalid JSON is ignored safely.
