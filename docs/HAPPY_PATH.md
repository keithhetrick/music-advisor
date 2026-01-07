# Music Advisor Happy Path (ma_helper front door)

Use `ma` as the single entrypoint. These commands are SAFE by default; actions that write require `--unlock-write` (or `MA_UNLOCK=write`).

- `ma doctor` — print Python/venv info and validate project registry.
- `ma graph` — show projects and dependency graph.
- `ma affected [--base origin/main]` — run affected tests (safe fallback warns if git base missing).
- `ma test --project <name>` — run a project test.
- `ma run <project[:target]>` — delegate to ma_orchestrator run/test target (requires `--unlock-write` for run).
- `ma smoke <audio_file>` — run the canonical full-chain smoke (requires `--unlock-write`).

Example workflow:

```bash
python -m ma_helper doctor
python -m ma_helper graph
python -m ma_helper test --project audio_engine
MA_UNLOCK=write python -m ma_helper smoke tone.wav
```

Deprecated direct invocations:

- Do not call `infra/scripts/*.sh` or the orchestrator script directly; use the `ma` equivalents above.
