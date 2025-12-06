# Frontend Handoff (Chat Host)

Share this with UI devs (macOS/web) to wire the app to `/chat`.

## Essentials
- Contract: `docs/frontend_contract_chat.md` (request/response, ui_hints, errors, CORS/auth).
- Samples: `docs/samples/chat_analyze_sample.json`, `docs/samples/chat_follow_structure_sample.json`.
- Collection: `docs/chat_stub_collection.json` (import into Postman/Insomnia).
- Env example: `docs/env.example.chat`.
- Docker: `docker/docker-compose.chat-stub.yml` + `docker/Dockerfile.chat` (stub + Redis).

## How to run the backend locally
- File sessions (default): `make chat-stub` (auto-kill, port 8090, sessions in data/sessions). Override `HOST_PORT/HOST_SESSION_STORE/HOST_SESSION_DIR`.
- Redis: `make chat-stub-redis` (requires `pip install redis` + Redis running).
- Dockerized stub+Redis: `make chat-stub-docker` or `docker-compose -f docker/docker-compose.chat-stub.yml up --build` (exposes 8090).
- CORS: set `HOST_CORS_ALLOW_ORIGIN=*` (or your origin) to emit CORS headers.
- Health: `curl http://localhost:8090/health`
- Clear sessions: `GET /admin/clear` (optional `HOST_ADMIN_TOKEN` for auth).

## Requests
- POST `/chat` with JSON:
  - `message`: intent or free text (intents mapped via `config/intents.yml`).
  - `payload`: /audio payload for analyze.
  - `norms`: optional market_norms snapshot.
  - `session`: send back the session object from the previous reply to preserve state.
  - `profile`: optional host profile (default `producer_advisor_v1`).
- GET `/health` for status.

## UI rendering tips
- Use `ui_hints.show_cards` to render cards (HCI, axes, optimization, historical echo).
- `quick_actions` → buttons; send `intent` as next `message`.
- `highlight_axes` → focus axes chart; `primary_slices` can order cards; `tone` can style copy.
- Show `warnings` unobtrusively. Support “help/tutorial/commands” with no payload for onboarding.
- Keep and resend `session` to preserve paging/history/recommendation.

## Error handling (surface to user)
- 400: invalid JSON/request.
- 401: unauthorized (if auth enabled).
- 413: payload/norms too large.
- 429: rate limit exceeded.
- 5xx: service unavailable; retry later.

## Auth/CORS
- Auth optional: static bearer (`HOST_AUTH_TOKEN`) or Google ID token (`HOST_GOOGLE_CLIENT_ID`). Send `Authorization` header if enabled.
- CORS: controlled via `HOST_CORS_ALLOW_ORIGIN` (gateway recommended for production).

## Dev defaults to recommend
- For macOS/local dev: `make chat-stub` (file store).
- For web/container: `make chat-stub-docker` (stub+Redis) or `make chat-stub-redis` with your own Redis.

