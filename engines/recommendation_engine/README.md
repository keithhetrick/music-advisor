# recommendation_engine

Deterministic Tier 2 engine: consumes `/audio` payloads + MARKET_NORMS snapshot → emits a structured recommendation/optimization plan. No scoring is recomputed; numbers are treated as ground truth.

## Layout

- `engine/recommendation.py` — core `compute_recommendation(payload, market_norms_snapshot)` logic.
- `engine/market_norms.py` — helpers for norms snapshot validation + percentile labeling.
- `tests/` — fixtures for payload + norms and behavior checks.

## Usage (dev)

```bash
# From repo root with PYTHONPATH=. or pip -e engines/recommendation_engine/recommendation_engine
python - <<'PY'
from recommendation_engine.engine.recommendation import compute_recommendation
from recommendation_engine.tests.fixtures import sample_payload, sample_market_norms
rec = compute_recommendation(sample_payload, sample_market_norms)
import json; print(json.dumps(rec, indent=2))
PY
```

## Contract

- Inputs:
  - `/audio` payload (features_full, audio_axes, HCI fields, historical_echo_v1).
  - `market_norms_snapshot` with region/tier/version, last_refreshed_at, quantiles for features + axes.
- Output: recommendation dict with HCI banding, axis interpretation, historical echo context, norm-relative positions, optimization suggestions, and `market_norms_used` tagging.

## Notes

- This engine is norm-aware; host/chat layers should call it rather than duplicating logic.
- Lives separate from `advisor_host` to keep the host thin and mono-repo friendly.

## Developer experience

- Headless/CLI-first: run via Python/CLI/tests; no UI required.
- Quick smoke (with `PYTHONPATH=.`): run the usage snippet above or `pytest engines/recommendation_engine/tests`.
- Remote/local wiring via env (`REC_ENGINE_MODE`, `REC_ENGINE_URL`); see `docs/engine_dynamic_knobs.md`.
- Minimal smoke command: `PYTHONPATH=. python - <<'PY'\nfrom recommendation_engine.engine.recommendation import compute_recommendation\nfrom recommendation_engine.tests.fixtures import sample_payload, sample_market_norms\nrec = compute_recommendation(sample_payload, sample_market_norms)\nprint('ok', bool(rec))\nPY`
