# Tutorials & Guided Modals (Concept)

Purpose: provide short, deterministic tutorials that can be shown as modals/steps in a UI or returned as structured text from the host layer. These are static (no LLM), so they can be pre-baked.

## Topics to cover

- What the app does (tiers, snapshots, host flow)
- How to analyze a track (upload → rec engine → host replies)
- How to enable norms (pass a snapshot path; what it means)
- How to use paging/quick actions (“more” for groove/loudness/plan)
- How to compare to previous
- Future-back mode (advisor_target.mode == future_back)
- Warnings/philosophy (HCI descriptive, not predictive)

## Suggested structure

- Title
- Steps (1–5 concise steps)
- Tips (short bullets)
- Links to relevant docs (architecture_overview, host_chat_behavior, host_response_schema)

## Representation (example JSON)

```json
{
  "tutorials": [
    {
      "id": "getting_started",
      "title": "Getting Started",
      "steps": [
        "Upload or provide an /audio payload.",
        "Optionally pass a market norms snapshot to enable norm-aware advice.",
        "Ask about tempo/groove/loudness/mood or say 'plan' if future-back sections exist.",
        "Use 'more' to page through detailed suggestions.",
        "Use 'compare' after a new payload to see what changed."
      ],
      "tips": [
        "HCI is descriptive, not predictive.",
        "Quick actions in ui_hints map to common follow-ups."
      ],
      "links": ["docs/host_chat_behavior.md", "docs/host_response_schema.md"]
    }
  ]
}
```

## Where to render

- Frontend/macos/web can render as modals or help panels.
- Host can expose a “tutorial” intent that returns one of these tutorials as text + UI hints.

## Tutorials (Pointers)

Short pointers to get oriented:

- Start with `docs/ops/operations.md` and `docs/ops/commands.md` for a full run/debug guide.
- For chat/host: `docs/host_chat/frontend_contracts.md` + `docs/host_chat/http_stub.md` (endpoints) + `docs/host_chat/host_response_schema.md`.
- For HCI: `docs/hci/hci_spec.md` (annotated) + HCI fields in pack/`hci.json`.
- For pipeline artifacts: `docs/pipeline/README_ma_audio_features.md` (merged/run_summary/audit) and `docs/pipeline/PIPELINE_DRIVER.md` (pack/audit tables).
- For norms: `docs/norms/market_norms.md` (build + anatomy).
- For sidecar: `docs/calibration/sidecar_tempo_key.md` (annotated sidecar JSON).
- For lyrics/TTC: `docs/lyrics/overview.md` + `docs/ttc/TTC_PLAN_v1.md`.
- For spine: `docs/spine/README.md` + `docs/spine/WORKFLOW.md`.

Use `docs/README.md` as the index if you get lost.

### Quick UI walkthrough (host/chat)

1. Start stub: `make chat-stub` (file store) or `make chat-stub-redis`.
2. POST a sample: `curl -X POST http://localhost:8090/chat -H "Content-Type: application/json" -d @docs/samples/chat_analyze_sample.json`.
3. Render the reply + `ui_hints`: show cards from `show_cards`, buttons from `quick_actions`, badge norms if present, and keep `session` to send on the next POST.

Schemas: `docs/schemas/host_response.schema.json` (reply/ui_hints/session). UI mock (text): `docs/host_chat/ui_mock/mock1.md`.
