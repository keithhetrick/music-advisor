# Frontend Contract & Handoff (Canonical)

Single reference for wiring macOS/web UI to `/chat`. Replaces `frontend_contract_chat.md` and `frontend_handoff.md` (archived).

## Contract (request/response)

- POST `/chat` with JSON:
  - `message`: intent or free text (`analyze | structure | groove | loudness | mood | historical | optimize | plan | compare | help | tutorial | commands | health | more | <free text>`). Intents map via `config/intents.yml`.
  - `payload`: optional `/audio` payload (include for `analyze`).
  - `norms`: optional `market_norms` snapshot.
  - `session`: send back the prior session object (at least `{session_id}`) to preserve state.
  - `profile`: optional host profile (default `producer_advisor_v1`).
- Response:
  - `reply`: `{session_id, reply, ui_hints}` where `ui_hints` can include `show_cards`, `quick_actions`, `highlight_axes`, `primary_slices`, `tone`, `warnings`.
  - `session`: `{session_id, host_profile_id, last_recommendation, prev_recommendation, last_intent, offsets, history...}` (persist + resend).
  - `user`: `null` unless auth is configured.

UI guidance:

- Use `ui_hints.show_cards` to decide cards (HCI, axes, optimization, historical echo).
- Render `quick_actions` as buttons (send `intent` next); use `highlight_axes` to focus charts; show `warnings` as non-blocking notices.
- Keep a local transcript; session history is available for reconciliation/debugging.
- Always resend `session` on follow-ups to keep paging/recommendation state.

### Flow (ASCII)

```ascii
[client UI] --POST /chat--> [host]
    |                         |
    |                 run recommendation (optional norms)
    |                         |
[render reply + ui_hints] <-- reply: {reply, ui_hints, session}
    |
[next intent] --POST /chat with session-->
```

### Tips for implementers

- Keep `session` on the client and resend it; server state is minimal by design.
- Render `warnings` as non-blocking notices; badge norms if present, otherwise show “advisory-only” copy.
- Treat `ui_hints.show_cards`/`primary_slices` as ordering hints; avoid hard-coding intent strings—pull from `config/intents.yml` if you need a list.
- Make “more” advance paging by sending the same intent with the preserved `session`.

### UI layout idea (text-only)

- **Header:** Track title/artist + norms badge (`US_Hot100Top40_2025-Q4` or “Advisory only”).
- **Cards (from `show_cards`):**
  - **HCI card:** final score + tier (from `.hci.json`), brief axis summary.
  - **Axes card:** chart of six axes (`audio_axes` order), highlight from `highlight_axes`.
  - **Optimization card:** top recommendations/plan from `reply`.
  - **Historical echo card:** primary decade + top neighbors; link to neighbors list.
- **Quick actions:** buttons from `quick_actions` (send `intent` on click).
- **Warnings:** inline banner from `ui_hints.warnings`.
- **Session handling:** store `session` and resend on every POST.

### Wireframe (text mock)

```text
[Header: <Track> — <Artist>] [Badge: Norms US_Hot100Top40_2025-Q4]

HCI (card)
  Score: 0.78  Tier: WIP-A   Decade: 1990s
  Axes: TempoFit↑ RuntimeFit→ LoudnessFit→ Energy→ Danceability↑ Valence→

Axes (card) [highlight: Energy, Danceability]
  Chart of six axes (0–1)

Historical Echo (card)
  Primary decade: 1990s
  Top neighbors: Song A (1995) · Song B (2001) · Song C (1989)
  [See all neighbors]

Optimization / Plan (card)
  - Tighten chorus LUFS to -9 dB
  - Raise Energy +0.05
  - (More)

Quick actions: [More groove] [Optimization next] [Plan] [Help]

Warnings (if any): Advisory-only (no norms provided)
```

More mock layouts: `docs/host_chat/ui_mock/mock1.md` (text mock; swap in screenshots later). Schema for responses: `docs/schemas/host_response.schema.json`.

## Local backend (dev) options

- File sessions (default): `make chat-stub` (auto-kill, port 8090, sessions in `data/sessions`; override `HOST_PORT/HOST_SESSION_STORE/HOST_SESSION_DIR`).
- Redis: `make chat-stub-redis` (requires `pip install redis` + Redis).
- Dockerized stub + Redis: `make chat-stub-docker` or `docker-compose -f docker/docker-compose.chat-stub.yml up --build` (exposes 8090).
- Health: `curl http://localhost:8090/health`; clear sessions: `GET /admin/clear` (optional `HOST_ADMIN_TOKEN`).
- CORS: set `HOST_CORS_ALLOW_ORIGIN=*` (or specific origin) to emit CORS headers.

## Error handling (surface in UI)

- `400` invalid JSON/request; `401` unauthorized (if auth enabled); `413` payload/norms too large; `429` rate limited; `5xx` service unavailable (retry).

## Quick references

- Samples: `docs/samples/chat_analyze_sample.json`, `docs/samples/chat_follow_structure_sample.json`.
- Collection: `docs/chat_stub_collection.json` (Postman/Insomnia import).
- Env example: `docs/host_chat/env.example.chat`.
- Host behavior/schema details: `docs/host_chat/host_chat_behavior.md`, `docs/host_chat/host_response_schema.md`, `docs/host_chat/http_stub.md`.
- Docker files: `docker/docker-compose.chat-stub.yml`, `docker/Dockerfile.chat`.

Archived originals: `docs/archive/host_chat/`.
