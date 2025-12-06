# Monorepo note (host addition)

- New host module (lowercase) added under `hosts/advisor_host/` with its own `pyproject.toml`, CLI (`ma-host`), and tests. It ingests `.client.*` payloads and emits advisory JSON; no scoring logic.
- Placeholder for future optimization engine at `engines/recommendation_engine/recommendation_engine/` to keep boundaries clear.
- Make target `test-advisor-host` runs host-only tests; `scripts/affected_host_tests.sh` can be used for change-scoped runs.
- Existing `.client.*` artifacts remain; they now include a header clarifying their role as client payloads for `advisor_host`.

This is preparatory groundwork for relocating to `hosts/advisor_host/` (and engines under `engines/`) in a future monorepo reorg.

Recommendation/optimization (Tier 2):

- `engines/recommendation_engine/recommendation_engine/` implements norm-aware advisory logic (`compute_recommendation`) and uses MARKET_NORMS snapshots. Tests live in `engines/recommendation_engine/recommendation_engine/tests`; run `make test-recommendation-engine`.

Host/Chat integration:

- `hosts/advisor_host/host/chat.py` is a thin intent router and session holder; `hosts/advisor_host/server.py` exposes a FastAPI `/chat` endpoint. Use `make run-chat-host` to run locally; defaults to loading `config/default_norms_path.txt` if not overridden.
