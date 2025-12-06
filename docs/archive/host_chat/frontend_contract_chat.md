# Frontend Contract — Chat Host

Goal: make a future UI trivial to wire up to `/chat`. This host is dumb (no GPT); all domain logic lives in the recommendation engine. The UI should:

1. POST `/chat` with JSON.
2. Render based on `reply` + `ui_hints`.
3. Preserve `session` from responses and send it back on follow-ups.

## Request shape

```json
{
  "message": "analyze | structure | groove | loudness | mood | historical | optimize | plan | compare | help | tutorial | health | commands | more | <free text>",
  "payload": {
    /* optional /audio payload */
  },
  "norms": {
    /* optional market_norms snapshot */
  },
  "session": {
    /* optional prior session snapshot; at least {session_id} */
  },
  "profile": "producer_advisor_v1" /* optional; default profile if omitted */
}
```

Minimum to get a useful answer: either

- `payload` present with `message: "analyze"` (generates a recommendation), or
- `message: "help"/"tutorial"/"commands"` to get guidance with no payload.

## Response shape

```json
{
  "reply": {
    "session_id": "...",
    "reply": "human-readable text",
    "ui_hints": {
      "show_cards": ["hci","axes","optimization","historical_echo"],
      "quick_actions": [{"label":"More structure","intent":"structure"}, ...],
      "highlight_axes": ["TempoFit","RuntimeFit"],
      "tone": "friendly",
      "primary_slices": ["axes","optimization","hci","historical"],
      "warnings": ["Norms snapshot may be stale."]
    }
  },
  "session": {
    "session_id": "...",
    "host_profile_id": "producer_advisor_v1",
    "last_recommendation": { ... recommendation object ... },
    "prev_recommendation": null,
    "last_intent": "structure",
    "offsets": {"structure": 0},
    "history": [
      {"role": "user", "content": "analyze"},
      {"role": "assistant", "content": "analysis_generated"},
      {"role": "user", "content": "structure"},
      {"role": "assistant", "content": "Structure highlights: ..."}
    ]
  },
  "user": null  /* set if auth is configured */
}
```

## UI rendering guide

- Cards: use `ui_hints.show_cards` to decide which sections to show (e.g., HCI card, axes chart, optimization list, historical echo).
- Quick actions: render buttons from `quick_actions` and send their `intent` as the next `message`.
- Highlight: use `highlight_axes` to focus the axes chart.
- Tone/primary_slices: optional styling/ordering hints for the UI.
- Warnings: show as non-blocking banners or notices.
- History: frontend may keep its own transcript; session.history can be used for reconciling state or debugging.
- Persist session: always send back the `session` object from the previous reply on follow-ups so state (recommendation, paging) is preserved.

## Common intents (suggested buttons)

- `analyze` (with payload), `structure`, `groove`, `loudness`, `mood`, `historical`, `optimize`, `plan`, `compare`, `help`, `tutorial`, `commands`, `health`, `more`.
- For typo-resilience, intents are mapped via `config/intents.yml`; free text is routed to the best-fit intent.

## Sample reply (abbreviated)

```json
{
  "reply": {
    "session_id": "abc123",
    "reply": "Structure highlights: TempoFit is strong; RuntimeFit is low...",
    "ui_hints": {
      "show_cards": ["axes", "optimization", "hci", "historical_echo"],
      "quick_actions": [{"label": "More structure", "intent": "structure"}],
      "highlight_axes": ["TempoFit", "RuntimeFit"],
      "tone": "friendly",
      "warnings": ["Norms snapshot may be stale."]
    }
  },
  "session": {
    "session_id": "abc123",
    "host_profile_id": "producer_advisor_v1",
    "last_recommendation": { "...": "..." },
    "last_intent": "structure",
    "history": [...]
  },
  "user": null
}
```

See `docs/samples/chat_analyze_sample.json`, `docs/samples/chat_analyze_no_norms.json`, `docs/samples/chat_analyze_no_hci.json`, `docs/samples/chat_analyze_experimental.json`, `docs/samples/chat_analyze_developing_historical.json`, `docs/samples/chat_analyze_strong_historical.json`, `docs/samples/chat_analyze_historical_rich.json`, and `docs/samples/chat_follow_structure_sample.json` for request examples.

## Sample cURL flow (local stub on 8090)

```bash
# 1) Merge payload (if needed)
python tools/merge_client_payload.py \
  --client /path/to/track.client.json \
  --hci /path/to/track.hci.json \
  --out /tmp/track.chat.json

# 2) Build analyze request (adds norms if present)
python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path("/tmp/track.chat.json").read_text())
req = {"message": "analyze", "payload": payload}
norms = Path("data/market_norms/market_norms_us_tier1_2024YE.json")
if norms.exists():
    req["norms"] = json.loads(norms.read_text())
Path("/tmp/chat_analyze.json").write_text(json.dumps(req, indent=2), encoding="utf-8")
PY

# 3) POST analyze
curl -s -X POST http://localhost:8090/chat \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/chat_analyze.json | jq . > /tmp/chat_reply.json

# 4) Follow-up (structure)
python - <<'PY'
import json, pathlib
resp = json.loads(pathlib.Path("/tmp/chat_reply.json").read_text())
sess = resp["session"]
pathlib.Path("/tmp/chat_follow.json").write_text(
    json.dumps({"message": "structure", "session": sess}, indent=2),
    encoding="utf-8",
)
PY
curl -s -X POST http://localhost:8090/chat \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/chat_follow.json | jq .
```

## Errors & handling

- 400 invalid JSON/request: show a friendly “request invalid; check payload/session format.”
- 401 unauthorized (if auth enabled): prompt to sign in or provide token.
- 413 too large: payload/norms exceeded caps; ask user to trim.
- 429 rate limit: show “too many requests; wait and retry.”
- 5xx: generic “service unavailable, try again.”

## Running the stub

- File-backed (default): `make chat-stub` (auto-kill, port 8090, sessions in `data/sessions`; override `HOST_PORT`, `HOST_SESSION_STORE`, `HOST_SESSION_DIR`).
- Redis (optional): `make chat-stub-redis` (requires `pip install redis` + running Redis; defaults `REDIS_URL=redis://localhost:6379/0`).
- Dockerized: `docker-compose -f docker/docker-compose.chat-stub.yml up --build` (brings up Redis + stub; exposes port 8090; set `HOST_CORS_ALLOW_ORIGIN` if needed).
- Health: `curl http://localhost:8090/health`
- Clear sessions: `GET /admin/clear` (optional bearer `HOST_ADMIN_TOKEN`).
- Engine remote mode (optional): host adapter supports `REC_ENGINE_MODE=remote` + `REC_ENGINE_URL=<http://engine:8100/recommendation>` to call a remote rec-engine service (see `engines/recommendation_engine/recommendation_engine/service.py`). Defaults to local engine calls. Engine service runner: `make rec-engine-service` starts the HTTP engine on port 8100 (POST /recommendation).

## Future UI checklist

- Map `ui_hints.show_cards` → cards/components (HCI, axes chart, optimization list, historical echo).
- Render `quick_actions` as buttons; send `intent` as next `message`.
- Preserve and resend `session` for continuity.
- Show `warnings` unobtrusively.
- Support “help/tutorial/commands” even with no payload, so new users get guidance immediately.
- Suggested mapping:
  - `hci` → HCI card (band + comment)
  - `axes` → axes/radar/levels with `highlight_axes`
  - `optimization` → list of suggestions
  - `historical_echo` → neighbors/decade info
  - `quick_actions` → buttons; `primary_slices` can order cards; `tone` can adjust copy style

## CORS/auth notes

- If serving to a browser, enable CORS at the API gateway (stub does not set CORS headers by default).
- Auth options: static bearer (`HOST_AUTH_TOKEN`) or Google ID token (`HOST_GOOGLE_CLIENT_ID`). If enabled, the UI should send appropriate headers (e.g., `Authorization: Bearer <token>`). Without auth, `user` stays null.
