# Samples

Reference payloads for chat/host testing:

- `chat_analyze_sample.json` — baseline analyze payload with norms.
- `chat_follow_structure_sample.json` — follow-up intent sample.
- `chat_analyze_no_norms.json` — analyze without norms snapshot.
- `chat_analyze_no_hci.json` — analyze without HCI.
- `chat_analyze_experimental.json` — experimental flags example.
- `chat_analyze_developing_historical.json` — developing historical echo.
- `chat_analyze_historical_rich.json` — richer historical context.
- `chat_analyze_strong_historical.json` — strong historical signal.

Use with `make chat-analyze` or POST to the chat stub (`/chat`).

## How to use (curl/Make)

Curl example (uses analyze sample):

```bash
curl -X POST http://localhost:8090/chat \
  -H "Content-Type: application/json" \
  -d @docs/samples/chat_analyze_sample.json
```

Make helper (merges client+HCI → chat JSON, posts to stub):

```bash
make chat-analyze CLIENT=/path/to/track.client.json HCI=/path/to/track.hci.json
```

Swap any sample JSON into the `-d @...` path to exercise other cases (no norms, no HCI, historical-heavy, etc.).

## Sample field expectations

- Each sample aligns with `docs/host_chat/frontend_contracts.md` request shape (`message`, `payload`, `norms`, `session`, `profile`).
- `payload` holds `/audio` fields (see `docs/EXTRACT_PAYLOADS.md`); `norms` may be present/absent depending on the sample.
- Use samples to validate host responses (`reply`, `ui_hints`, `session`), or to sanity-check `/chat` wiring without generating artifacts.

### Expected response (when posting samples)

- `reply.reply` — human-readable text summarizing analysis.
- `reply.ui_hints` — cards to render (`show_cards`), quick actions (`quick_actions`), axes to highlight, tone, warnings.
- `session` — session state to resend; contains `session_id`, last/prev recommendations, offsets, history.
- If norms absent in the sample, expect an advisory-only warning in `warnings`.
