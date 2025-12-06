# HTTP Stub (advisor_host)

This is a minimal HTTP wrapper around the deterministic chat handler. It reuses the same request/response shapes as the CLI/chat.

## Endpoints (what they do)

- `POST /chat` — main entry; send `{message, payload?, norms?, session?, profile?}`. Returns `{reply, ui_hints, session}`. Same shape as CLI (see `docs/host_chat/frontend_contracts.md`).
- `GET /health` — liveness probe (`{status, message}`).
- `GET /` — usage JSON or tiny HTML form if `Accept: text/html`.
- `GET /admin/clear` — clears sessions (requires `HOST_ADMIN_TOKEN` if set).

## Run

```bash
HOST_LOG_PATH=logs/host.jsonl python -m advisor_host.cli.http_stub
# override port:
# HOST_PORT=8091 HOST_FORCE_PORT=1 HOST_LOG_PATH=logs/host.jsonl python -m advisor_host.cli.http_stub
```

## Example payloads

Use `docs/host_chat/chat_stub_collection.json` (Postman/Insomnia) or curl a sample:

```bash
curl -X POST http://localhost:8090/chat \
  -H "Content-Type: application/json" \
  -d @docs/samples/chat_analyze_sample.json
```

## Notes

- No authentication by default; intended for local/dev use.
- Logging: set `HOST_LOG_PATH` to append JSONL logs (intent, norms-present, rec_version, advisor_mode, reply length, \_more).
- Behavior matches CLI: deterministic, no LLM, uses profile/tone/phrasing configs.

### Quick visual (endpoints)

```bash
GET /health           -> {status, message}
POST /chat            -> {reply, ui_hints, session}
GET /                 -> usage JSON or tiny HTML form
GET /admin/clear      -> clears sessions (token if set)
```

Schema for responses: `docs/schemas/host_response.schema.json`.
