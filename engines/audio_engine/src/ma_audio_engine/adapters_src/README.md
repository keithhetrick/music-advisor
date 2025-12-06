# Adapters

Modular shims used across the pipeline. Each adapter may read an optional config file in `config/` to change behavior without code edits. Inline docstrings include quick usage snippets.

- `audio_loader_adapter.py` — load audio (defaults to librosa); optional `config/audio_loader.json` for backend/mono.
- `backend_registry_adapter.py` — sidecar backends/default cmd; optional `config/backend_registry.json`. Usage: `list_supported_backends()`, `get_sidecar_cmd_for_backend("essentia")`.
- `cache_adapter.py` — cache backend/dir; optional `config/cache.json`. Usage: `get_cache(cache_dir=".ma_cache", backend="noop|disk")`.
- `confidence_adapter.py` — tempo confidence bounds/labels; optional `config/tempo_confidence_bounds.json`. Usage: `normalize_tempo_confidence(raw, backend="essentia")`.
- `config_adapter.py` — config fingerprint components.
- `hash_adapter.py` — file hashing algo/chunk; optional `config/hash.json`.
- `logging_adapter.py` — log prefix/redaction/secrets; optional `config/logging.json`. Usage: `make_logger(...)`, `make_structured_logger(...)`, `sandbox_scrub_payload(...)`.
- `neighbor_adapter.py` — neighbor file writer/schema guard. Usage: `write_neighbors_file(path, payload, max_neighbors=..., max_bytes=...)`.
- `qa_policy_adapter.py` — QA policy loader; optional `config/qa_policy.json`. Usage: `load_qa_policy("strict", overrides=...)`.
