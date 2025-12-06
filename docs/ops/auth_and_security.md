# Auth & Security Notes (advisor_host)

## Why this exists

- Host/chat defaults to local/dev. These toggles let you add minimal auth and guardrails when exposing it (tokens, CORS, size/rate limits, sandbox logging).
- Keep defaults safe: deterministic replies, no external calls unless configured, redaction/sandbox options.

## Auth options

- **Google ID tokens (recommended)**: Set `HOST_GOOGLE_CLIENT_ID`; incoming requests must present `Authorization: Bearer <id_token>`. We verify issuer, audience, expiry, and best-effort JWK presence (full signature verification recommended in production).
- **Optional signature verification**: set `HOST_VERIFY_GOOGLE_SIG=true` and ensure PyJWT is available to validate against Google JWKs.
- **Static bearer (dev fallback)**: Set `HOST_AUTH_TOKEN`; incoming `Authorization: Bearer <token>` is accepted and mapped to a synthetic user.
- **Admin endpoint**: `/admin/clear` protected by `HOST_ADMIN_TOKEN` when set; clears sessions and rate-limit counters.

## Limits & quotas

- Request size: `HOST_MAX_BODY_BYTES`, `HOST_MAX_PAYLOAD_BYTES`, `HOST_MAX_NORMS_BYTES`.
- Rate limits: `HOST_RATE_WINDOW_SECS`, `HOST_RATE_LIMIT` (per user/id or IP).
- History/reply/advisory caps: `HOST_MAX_HISTORY_BYTES`, `HOST_MAX_REPLY_BYTES`, `HOST_MAX_ADVISORY_BYTES`.

## Logging & diagnostics

- Logs: `HOST_LOG_PATH` (+ rotation via `HOST_LOG_MAX_BYTES`, `HOST_LOG_BACKUPS`); logs are JSONL and can be exported redacted via `diagnostics_cli`.
- Diagnostics email: `HOST_DIAGNOSTICS_EMAIL` (default [keith@bellweatherstudios.com](mailto:keith@bellweatherstudios.com)); bundles are redacted and hashed.
- Avoid logging payload bodies; quick actions and ui_hints are sanitized/allowlisted.

## Session storage

- Default in-memory; optional file store; optional Redis via `REDIS_URL`. Session stores support `clear()` for cache cleanup.

## Privacy hygiene

- No payload contents in diagnostics by default; hashes user ids in exports.
- Strip tokens/large fields via allowlists/drop lists; sanitize/size-cap replies and history.

## Hardening checklist for production

- Add full JWK signature verification for ID tokens.
- Enforce HTTPS/localhost binding for the stub; set CORS if exposed.
- Add secret management (do not bake secrets in binaries).
- Add real metrics/tracing exporter (Prom/OTEL) with correlation IDs.
- Enable `LOG_REDACT=1` and `LOG_SANDBOX=1` to mask values and drop beats/neighbors in logs if you need safer logging.

### Sample env (local with bearer)

```bash
export HOST_AUTH_TOKEN="dev-token"
export HOST_LOG_PATH="logs/host.jsonl"
export HOST_LOG_MAX_BYTES=1048576
export HOST_LOG_BACKUPS=5
export HOST_MAX_BODY_BYTES=5242880
export HOST_MAX_PAYLOAD_BYTES=1048576
export HOST_MAX_NORMS_BYTES=524288
export HOST_MAX_REPLY_BYTES=16384
export HOST_MAX_HISTORY_BYTES=32768
export HOST_MAX_ADVISORY_BYTES=8192
export HOST_RATE_WINDOW_SECS=60
export HOST_RATE_LIMIT=120
export LOG_REDACT=1
export LOG_SANDBOX=1
python -m advisor_host.cli.http_stub
```
