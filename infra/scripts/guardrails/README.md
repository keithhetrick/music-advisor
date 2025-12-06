# Guardrail scripts

Convenience runners grouped here for clarity. Originals remain in `scripts/` to avoid breaking existing automation.

- `run_echo_inject_guardrails.sh` — injects echo/client with tempo-confidence on and QA defaults.
- `run_rank_with_guardrails.sh` — ranker with QA defaults and summarize-qa.
- `run_extract_strict.sh` — extraction with strict QA.
- `qa_automator_probe.sh` — probe automator output with QA checks.

These are copies of the top-level scripts; update both locations if you change behavior.
