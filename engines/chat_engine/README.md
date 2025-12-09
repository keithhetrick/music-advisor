# Chat Engine (stub)

Goal: a single, reusable entrypoint for chat that the macOS app, CLI, or other hosts can call. This is a scaffold that reuses the existing `tools/chat` backend; we keep the API stable while we evolve the internals.

## Design

- Inputs: `prompt`, `context` (sidecar/client.rich path, selection label), optional rate/error flags.
- Output: `reply`, `label`, `warning`, `rateLimited`, `timedOut`.
- Implementation: thin wrapper that shells out to `tools/chat/chat_router.py` (future: direct Python module import).
- Real-time safety: chat is never on the audio thread; always off the UI thread.

## Suggested API (Swift side)

Expose a minimal protocol in the host app, implemented by a concrete provider that calls this engine:

```Swift
struct ChatRequest {
  let prompt: String
  let contextPath: String?
  let label: String
}

struct ChatResponse {
  let reply: String
  let label: String
  let warning: String?
  let rateLimited: Bool
  let timedOut: Bool
}
```

## Current state

- Uses existing `tools/chat/chat_router.py` via this engine.
- Provides JSON output via `chat_cli.py` for hosts to consume.

### Smokes

```bash
cd engines/chat_engine
python cli_smoke.py
# JSON-emitting CLI:
python chat_cli.py --prompt "Hello" --context /path/to/file.client.rich.txt
# Contract smoke (checks output keys):
python contract_smoke.py
# Contract test:
PYTHONPATH=.. python test_contract.py
```

### Next steps

- Add tests/fixtures to keep the interface stable for all hosts.
