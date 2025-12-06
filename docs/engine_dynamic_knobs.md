# Engine connection points & dynamic knobs

This repository is designed for modular, swappable backends. Key connection points expose environment-variable toggles to keep integrations dynamic and headless-friendly.

## Chat / host

- Delegation to modular chat backend: `HOST_CHAT_BACKEND_MODE=on|auto|off` + `client_rich_path` in requests (HTTP stub/FastAPI). Optional: `HOST_CHAT_BACKEND_MAXLEN`, `CHAT_PARAPHRASE_ENABLED`.
- Host HTTP stub: `HOST_MAX_BODY_BYTES`, `HOST_MAX_PAYLOAD_BYTES`, `HOST_MAX_NORMS_BYTES`, `HOST_SESSION_STORE` (memory|file|redis), `HOST_PORT`, `HOST_AUTH_TOKEN`, `HOST_GOOGLE_CLIENT_ID`.
- Recommendation adapter (used by host): `REC_ENGINE_MODE=local|remote`, `REC_ENGINE_URL` when remote.

## Recommendation engine

- Service: `REC_ENGINE_PORT` (default 8100). Designed to be called via adapter toggles above; use remote mode to decouple host from local engine.

## Audio engine

- Plugin DI/env selectors:
  - Cache plugin: `MA_CACHE_PLUGIN`
  - Sidecar plugin: `MA_SIDECAR_PLUGIN`
  - Exporter plugin: `MA_EXPORTER_PLUGIN`
  - Logging plugin: `MA_LOGGING_PLUGIN`
  - CLI/config adapters read env overrides via `config_adapter.py`/`cli_adapter.py`.
- Misc knobs: `MA_DISABLE_NORMS_ADVISORY` (sentinel_validate), log redaction (`LOG_REDACT`, `LOG_REDACT_VALUES`).

## Lyrics engine / STT

- Whisper backend: `LYRIC_STT_SEPARATOR_CMD`, `LYRIC_STT_WHISPER_MODEL` (default medium), `LYRIC_STT_ALT_MODEL` (default medium).
- LCI export: `LYRIC_LCI_NORMS_PATH`.
- Log redaction: `LOG_REDACT`, `LOG_REDACT_VALUES`.

## TTC engine

- TTC engine: remote mode via `TTC_ENGINE_MODE=local|remote` and `TTC_ENGINE_URL` when remote (required). TTC sidecar allows env fallback `TTC_OPTS` for seconds-per-section/profile when CLI flags are at defaults and optional timeout via `TTC_TIMEOUT_SECONDS`. Logging via `LOG_JSON`/redaction flags.

## Quick headless smokes (per component)

- Chat/host: `make -f docs/Makefile.sparse-smoke sparse-smoke-chat`
- Sidecars: tempo/key/TTC: `make -f docs/Makefile.sparse-smoke sparse-smoke-tempo|key|ttc`
- Recommendation engine: `make -f docs/Makefile.sparse-smoke sparse-smoke-reco`

## Guidance for future connection points

- Provide an env-switchable mode (local|remote or plugin name) for each adapter boundary.
- Keep defaults backward-compatible; fail fast if a required URL/path is missing in remote mode.
- Document new knobs in the relevant README and in this file to aid sparse/headless development.
