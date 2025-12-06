# Host Response Schema (Deterministic)

Each chat/CLI reply uses this shape:

```json
{
  "session_id": "<uuid>",
  "reply": "<text payload>",
  "ui_hints": {
    "show_cards": ["hci", "axes", "optimization", "historical_echo"],
    "quick_actions": [{"label": "More groove", "intent": "groove"}],
    "highlight_axes": ["Energy", "Danceability"],
    "tone": "friendly|direct|neutral",
    "primary_slices": ["axes", "optimization", ...],
    "warnings": []                // optional
  },
  "market_norms_used": {          // from recommendation
    "region": "...",
    "tier": "...",
    "version": "...",
    "last_refreshed_at": "..."
  },
  "rec_version": "...",           // if passed through from recommendation
  "advisor_mode": "future_back|optimize_current"  // if present in recommendation
}
```

## Annotated example (truncated)

```json
{
  "session_id": "3b8e-...",
  "reply": "HCI is advisory-only; norms snapshot US_Hot100Top40_2025-Q4 applied. Axes: TempoFit high...",
  "ui_hints": {
    "show_cards": ["hci", "axes", "optimization", "historical_echo"],
    "quick_actions": [
      { "label": "More groove", "intent": "groove" },
      { "label": "Optimization next", "intent": "optimize" }
    ],
    "highlight_axes": ["Energy", "Danceability"],
    "tone": "friendly",
    "primary_slices": ["axes", "optimization", "historical_echo"],
    "warnings": ["Using norms snapshot US_Hot100Top40_2025-Q4"]
  },
  "market_norms_used": {
    "region": "US",
    "tier": "Hot100Top40",
    "version": "2025-Q4",
    "last_refreshed_at": "2025-12-01T00:00:00Z"
  },
  "rec_version": "1.4.0"
}
```

What to render:

- `reply` is the narrative; `ui_hints` drives cards/buttons/highlights.
- `market_norms_used` should surface in UI as a badge or warning; if absent, show an advisory-only note.
- `quick_actions.intent` must map to allowed intents from `config/intents.yml`.
- `session` carries paging/history/last recommendation; always resend it on follow-ups.

Notes:

- `reply` is plain text concatenated from slice formatters (axes/groove/loudness/mood/historical/optimization/plan/compare).
- `ui_hints` informs a UI which cards to show, which axes to highlight, and suggested follow-up actions.
- `quick_actions.intent` values map to chat intents; “more” paging is supported when `_more` is true internally. Intents include structure, groove, loudness, mood, historical, optimize, general, plan, compare, health, tutorial, capabilities, summarize, expand.
- Norms metadata and warnings are appended to replies for transparency.
- If norms are absent, `market_norms_used` is `None` and reply contains an advisory-only note.

### UI rendering (text sketch)

```bash
[Reply text block]

Cards (from ui_hints.show_cards):
  - HCI: score/tier, axes summary (highlight_axes emphasized)
  - Axes: chart of six axes
  - Optimization/Plan: top recs/steps
  - Historical echo: decade + neighbors

Quick actions: buttons from ui_hints.quick_actions (send intent)
Warnings: inline badge from ui_hints.warnings or missing norms
```

Schema: `docs/schemas/host_response.schema.json`.

Contracts:

- No new scores are computed; replies only interpret provided recommendation fields.
- `ui_hints` keys are stable; additional keys may be added but existing ones are not repurposed.
