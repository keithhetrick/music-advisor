# Pipelines (orchestration)

This folder hosts high-level runners for the MusicAdvisor AudioTools stack. Originals remain in their prior locations for backward compatibility; use these copies for a clearer, professional layout.

Included scripts (mirrors of top-level/scrips versions):
- `automator.sh` — main drag-and-drop/CLI automator
- `automator_full.sh` — full automator variant
- `run_full_pipeline.sh` — orchestrated end-to-end run
- `run_extract_strict.sh` — extraction with strict QA
- `run_echo_inject_guardrails.sh` — echo/client inject with guardrails
- `run_rank_with_guardrails.sh` — ranker with QA defaults and summarize-qa
- `qa_automator_probe.sh` — QA probe for automator output

Notes:
- These are copies; top-level/scrips versions still exist to avoid breaking existing automation. Prefer these paths for new docs and onboarding.
- See `COMMANDS.md` and tool READMEs for usage details.
