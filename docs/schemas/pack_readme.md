# Schemas (JSON)

Machine-readable references for common artifacts. Draft-07 JSON Schema; flexible (additional properties allowed) but captures core fields.

- `pack.schema.json` — pack payload (bundle for apps).
- `engine_audit.schema.json` — provenance for full runs.
- `run_summary.schema.json` — per-run provenance next to HCI/client files.
- `hci.schema.json` — `.hci.json` shape (scores, axes, historical echo).
- `neighbors.schema.json` — `.neighbors.json` shape (neighbors + meta).
- `ttc_annotations.schema.json` — TTC sidecar annotations.
- `host_response.schema.json` — `/chat` response shape (reply/ui_hints/session).
- `market_norms.schema.json` — norms snapshot shape (region/tier/version/percentiles/axes).

Current artifact set (12-file payload emitted by Automator/pipeline; adds tempo_norms + tempo overlay):

- `<stem>_<ts>.features.json`
- `<stem>.sidecar.json`
- `<stem>.tempo_norms.json`
- `<stem>_<ts>.merged.json`
- `<stem>_<ts>.hci.json`
- `<stem>_<ts>.ttc.json`
- `<stem>.neighbors.json`
- `<stem>.client.txt` / `<stem>.client.json`
- `<stem>.client.rich.txt` / `<stem>.client.rich.json`
- `run_summary.json`
- `<stem>_<ts>.pack.json` (full mode)
- `engine_audit.json` (full mode)

See related docs for narratives: pipeline (`docs/pipeline/`), HCI (`docs/hci/hci_spec.md`), TTC (`docs/ttc/TTC_PLAN_v1.md`), host/chat (`docs/host_chat/`).
