# advisor_host (dumb host layer)

Lowercase, standalone host that reads precomputed `/audio import {…}` payloads (e.g., `.client.json` / `.client.rich.txt`) and emits a structured advisory JSON for UI/GPT/macOS wrappers. No scoring or feature math lives here; all numbers are treated as ground truth.

## Layout

- `host/adapter.py` — parse helper text or raw JSON into a payload dict.
- `host/advisor.py` — deterministic advisory logic (canonical HCI selection, banding, axis + historical echo interpretation, suggestions).
- `host/schemas.py` — light typing/contracts for payloads and advisories.
- `cli/ma_host.py` — tiny CLI: read helper text/JSON, emit advisory JSON to stdout.
- `tests/` — minimal fixtures to pin behavior.

## Usage (dev)

```bash
# From repo root with PYTHONPATH=. or pip -e hosts/advisor_host
python hosts/advisor_host/cli/ma_host.py path/to/sample.client.json
# Or pipe helper text containing /audio import {…}
cat sample.client.rich.txt | python hosts/advisor_host/cli/ma_host.py
# Norm-aware path (needs market_norms_snapshot JSON)
python hosts/advisor_host/cli/ma_host.py --norms data/market_norms/market_norms_us_tier1_2024YE.json path/to/sample.client.json

# Run chat HTTP shim (FastAPI)
uvicorn advisor_host.server:app --reload --port 8080
curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" \
  -d '{"message":"help","audio_payload":{}}'

# Quick help target (Makefile)
make host-cli-help
```

Quick tests: `./scripts/quick_check.sh` (full suite). For host-only focus, run `PYTHONPATH=hosts/advisor_host python -m pytest hosts/advisor_host/tests -q`.

## Contract

- Inputs: dict payload matching the existing `.client.json` shape produced by `pack_writer.build_client_helper_payload` (see `docs/host_inputs.md`).
- Output: advisory dict:
  - `canonical_hci`, `canonical_hci_source`, `hci_band`, `hci_comment`
  - `axes` (per-axis value/level/comment)
  - `historical_echo`
  - `optimization` suggestions
  - `disclaimer`, `warnings`

## Notes

- Filenames `.client.json/.client.rich.txt` stay the same for compatibility; they represent client-facing payloads the host ingests.
- This module is intentionally decoupled so it can be moved under `hosts/advisor_host/` in a future monorepo. Root `ma_host` shim forwards here; archive shims removed.
- Optional: set `HOST_CHAT_BACKEND_MODE=on` and provide `client_rich_path` to delegate chat replies to the modular `tools/chat` backend while keeping the host as a thin front door.

## Chat-only workflow (sparse checkout friendly)

If you only want to work on chat/host:

- Sparse checkout: `git clone --filter=blob:none <repo> && cd MusicAdvisor_AudioTools && git sparse-checkout init --cone && git sparse-checkout set hosts/advisor_host tools/chat shared`
- Install minimal deps: `pip install -e hosts/advisor_host -e tools/chat` (set `PYTHONPATH=.` for tests/CLI).
- Run chat tests: `pytest hosts/advisor_host/tests hosts/advisor_host/tests/test_chat_backend_adapter.py`
- Smoke the host: `python -m advisor_host.cli.http_stub` (optional `HOST_CHAT_BACKEND_MODE=on` + `client_rich_path` to exercise tools/chat backend).

### What to expect while developing chat-only

- Edit surface: business logic and responses live in `tools/chat/*` (intents/router/overlay dispatch); host stays thin in `hosts/advisor_host/host/*`.
- Fast feedback:

  - Unit tests: `pytest hosts/advisor_host/tests` for host plumbing; add focused tests under `hosts/advisor_host/tests` for new host hooks, and under `tools/chat/tests` (if present) for chat logic.
  - Manual smoke via HTTP stub: `HOST_CHAT_BACKEND_MODE=on python -m advisor_host.cli.http_stub` then POST `/chat` with JSON:

    ```json
    {
      "message": "tempo?",
      "client_rich_path": "/abs/path/to/song.client.rich.txt"
    }
    ```

    You should see a concise reply (tempo/key/intent-aware). Remove `client_rich_path` or set `HOST_CHAT_BACKEND_MODE=off` to see host-only fallback.

- CLI (no backend delegation): `cat sample.client.rich.txt | python -m advisor_host.cli.ma_host` to verify advisory path still works.

- Minimal dependencies: engines are not required unless you call them explicitly; shared libs under `shared/` must stay on `PYTHONPATH`.
- Toggle behavior: `HOST_CHAT_BACKEND_MODE=on|auto|off`; `client_rich_path` must point at a `.client.rich.txt` for overlay answers. When off/absent, host replies with its built-in formatter.
- Developer experience: headless/CLI-first; exercise responses via CLI or the HTTP stub, no UI required.

### Dynamic toggles (summary)

- Chat delegation: `HOST_CHAT_BACKEND_MODE=on|auto|off` (+ `client_rich_path` in the request). Optional paraphrase hook: `CHAT_PARAPHRASE_ENABLED=1`. Optional max length: `HOST_CHAT_BACKEND_MAXLEN`.
- Recommendation engine: `REC_ENGINE_MODE=local|remote` and `REC_ENGINE_URL` when remote (used by `recommendation_adapter`).
- Host HTTP stub: `HOST_MAX_BODY_BYTES`, `HOST_MAX_PAYLOAD_BYTES`, `HOST_MAX_NORMS_BYTES`, `HOST_SESSION_STORE` (memory|file|redis), `HOST_PORT`, `HOST_AUTH_TOKEN`, `HOST_GOOGLE_CLIENT_ID`.
