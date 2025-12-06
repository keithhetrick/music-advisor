# Host/Chat Behavior (Stateful, Slice-Aware)

This host chat layer remains thin and deterministic, but now supports:

- Session state: remembers last recommendation, intent, paging offset, and history.
- Slice-aware replies: intents map to specific parts of the recommendation (HCI/axes, groove, loudness, mood, historical echo, optimizations).
- Paging: “more” advances through axes, historical echo notes, and optimizations.
- Quick actions: `ui_hints.quick_actions` suggest follow-ups (e.g., “More groove”).
- Norms metadata: replies include which norms snapshot is used, or an advisory-only warning if none.
- Profiles: `hosts/advisor_host/config/host_profiles.yml` sets tone and primary slice order hints (exposed in `ui_hints`).
- Profile phrasing: the same YAML can override per-intent phrasing (structure/groove/loudness/mood/historical/optimization/plan/compare/capabilities) to adjust tone/wording without code changes.
- Session persistence: save/load session JSON for continuity across runs.
- Help/capabilities/tutorial: respond even before analysis, with quick-start guidance and quick actions to “Getting started”/“Commands”.
- Intents config: `config/intents.yml` supplies synonyms; quick actions are allowlisted/sanitized.
- Optional Redis session store: use `REDIS_URL` to enable `RedisSessionStore`; otherwise in-memory/file stores.
- Plan intent: if `advisor_sections` exists (future-back / structured advisory), use intent “plan” to surface CURRENT_POSITION, DESTINATION, GAP_MAP, REVERSE_ENGINEERED_ACTIONS, PHILOSOPHY_REMINDER (or RECOMMENDED_NEXT_MOVES for optimize-current).
- Capabilities/health/tutorial intents: available to surface help, status, and a “what can you do” summary.
- Byte budgets: history/reply/advisory retention enforced via env caps; oversized replies truncate with warnings.
- Diagnostics export: `python -m advisor_host.cli.diagnostics_cli --log LOG --user-id X --app-version Y` produces a redacted, size-capped bundle (support email via `HOST_DIAGNOSTICS_EMAIL`).
- Golden transcripts: `hosts/advisor_host/tests/golden_chat.json` + `test_golden_transcripts.py` exercise CLI flows and validate schema compliance.

## Flow (at a glance)

```ascii
[payload + message] --POST /chat--> host
   |                         |
   |                 recommendation (optional norms)
   |                         |
[reply + ui_hints + session] <-- host
   |
[send next intent with session_id]
```

UI should render `reply`, show cards from `ui_hints.show_cards`, add buttons from `quick_actions`, badge norms or advisory-only warnings, and always resend `session` on the next call.

## CLIs

- Main host CLI: `hosts/advisor_host/cli/ma_host.py` (ingests helper text/JSON; optional `--norms`).
- Session CLI (load/save): `python -m advisor_host.cli.session_cli --message "..." [--payload path] [--norms path] [--load path] [--save path]`
- Chat stub:
  - Preferred: `make chat-stub` (auto-kill the port, defaults to port 8090, file-backed sessions in `data/sessions`). Override with `HOST_PORT=...`, `HOST_SESSION_STORE=memory|file|redis`, `HOST_SESSION_DIR=...`.
  - Direct: `HOST_PORT=8090 HOST_FORCE_PORT=1 PYTHONPATH=hosts:engines:engines/recommendation_engine .venv/bin/python hosts/advisor_host/cli/http_stub.py` (POST /chat; GET /health; GET / returns usage JSON or tiny HTML form if `Accept: text/html`; GET /admin/clear clears sessions).
  - Redis helper: `make chat-stub-redis` (needs `pip install redis` + a running Redis server, defaults `REDIS_URL=redis://localhost:6379/0`).

## UI Hints

Replies include `ui_hints` to help a frontend render cards/buttons:

- `show_cards`: e.g., `["hci","axes","optimization","historical_echo"]`
- `quick_actions`: suggested follow-ups
- `highlight_axes`: axes to emphasize in the current slice
- `tone`, `primary_slices`: hints from the active profile

## Paging

- Use “more” to page through optimizations, axes slices (structure/groove/loudness/mood), or historical echo notes.
- Missing fields (HCI/audio_axes) emit remediation warnings and quick actions to tutorial/commands.

## Profiles

- Defined in `hosts/advisor_host/config/host_profiles.yml`.
- Currently influence `tone`/`primary_slices` hints; phrasing can be extended per profile if desired.

## Persistence

- Session JSON can be saved/loaded via `session_cli.py`.
- Stored fields: session_id, profile, last recommendation, last intent/offset, history.

## Tests

- Coverage for norms/no-norms, paging, history, and session save/load:
  - `hosts/advisor_host/tests/test_chat.py`
  - `hosts/advisor_host/tests/test_cli_norms.py`
  - `hosts/advisor_host/tests/test_session_cli.py`
  - `hosts/advisor_host/tests/test_golden_flow.py`

## Quick CLI walk-through (local stub)

Terminal 1 – start stub (auto-kill port, file-backed sessions by default):

```bash
make chat-stub
# or override:
# HOST_PORT=8091 HOST_SESSION_STORE=memory make chat-stub
# HOST_SESSION_STORE=redis REDIS_URL=redis://localhost:6379/0 make chat-stub-redis  (requires redis package + server)
```

Terminal 2 – analyze + follow-up for a track (example paths):

```bash
# Merge client + HCI into chat-ready payload
python tools/merge_client_payload.py \
  --client "/Users/keithhetrick/music-advisor/data/features_output/2025/12/03/TRACK IS CRAZY_ GTHOT/TRACK IS CRAZY_ GTHOT.client.json" \
  --hci "/Users/keithhetrick/music-advisor/data/features_output/2025/12/03/TRACK IS CRAZY_ GTHOT/TRACK IS CRAZY_ GTHOT.hci.json" \
  --out /tmp/track.chat.json

# Build analyze request (adds norms if present)
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

# POST analyze, capture reply
curl -s -X POST http://localhost:8090/chat \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/chat_analyze.json | jq . > /tmp/chat_reply.json

# Build follow-up from returned session
python - <<'PY'
import json, pathlib
resp = json.loads(pathlib.Path("/tmp/chat_reply.json").read_text())
sess = resp["session"]
pathlib.Path("/tmp/chat_follow.json").write_text(
    json.dumps({"message": "structure", "session": sess}, indent=2),
    encoding="utf-8",
)
PY

# POST follow-up (e.g., structure intent)
curl -s -X POST http://localhost:8090/chat \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/chat_follow.json | jq .
```

## Runtime/env toggles

- Logging/rotation: `HOST_LOG_PATH`, `HOST_LOG_MAX_BYTES`, `HOST_LOG_BACKUPS`
- HTTP limits: `HOST_RATE_WINDOW_SECS`, `HOST_RATE_LIMIT`, `HOST_MAX_BODY_BYTES`
- Session store: `REDIS_URL` (optional Redis), otherwise in-memory/file
- Metrics: emitted via logger (can be ingested by an external collector)
- Payload/norms caps: `HOST_MAX_PAYLOAD_BYTES`, `HOST_MAX_NORMS_BYTES`; history/reply/advisory caps `HOST_MAX_HISTORY_BYTES`, `HOST_MAX_REPLY_BYTES`, `HOST_MAX_ADVISORY_BYTES`
- Auth: `HOST_GOOGLE_CLIENT_ID` (Google ID tokens, best-effort JWK check), `HOST_AUTH_TOKEN` (static bearer), `HOST_ADMIN_TOKEN` (admin clear endpoint)
- Diagnostics: `HOST_DIAGNOSTICS_EMAIL` sets the support email; diagnostics bundle is redacted/hashed
- Metrics: optional Prom exporter via `HOST_PROM_ENABLED=true` (requires `prometheus_client`)
- Payload helper: `python tools/merge_client_payload.py --client path/to/track.client.json --hci path/to/track.hci.json --out /tmp/track.chat.json` (merges axes/HCI/historical into a chat-ready payload).
