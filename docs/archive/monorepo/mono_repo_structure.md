## Mono-Repo Structure (Current)

- `hosts/`
  - `advisor_host/` — Python host/chat shell (thin orchestrator; reusable concern packages inside).
- `engines/`
  - `recommendation_engine/` — core recommendation/advisory logic.
- `archive/`
  - `builder_pack/` — legacy GPT builder assets (prompts/router/policies); not used at runtime.
- `vendor/` — now reserved for third-party/legacy deps (should shrink over time).

Other top-level dirs remain as before (data, scripts, notebooks, etc.). This layout is ready for mono-repo tooling and clarifies boundaries: hosts vs engines vs archived assets. Imports have been updated to reflect the moves.
