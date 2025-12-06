# Docs Index

Organized by theme with canonical entrypoints; archived legacy copies live under `docs/archive/`.

- **Start Here (5-minute tour)**

  1. Read `docs/ops/operations.md` (install/run/validate/debug).
  2. Skim `docs/architecture/README.md` (flow and tiers).
  3. If using chat: `docs/host_chat/frontend_contracts.md` + `docs/samples/README.md`.
  4. For HCI details: `docs/hci/hci_spec.md`.
  5. For market context: `docs/norms/market_norms.md`.
  6. Running locally (macOS): `docs/integrations/macos.md`.
  7. Lyrics/TTC: `docs/lyrics/overview.md`.

- **Architecture** — `docs/architecture/README.md` (canonical), `file_tree.md`, `repo_structure.md`, `components.md`, `adapters.md`, `modularity_map.md`.
- **Ops** — `docs/ops/operations.md` (whitepaper), `docs/ops/commands.md` (cheatsheet), config/auth notes, tutorials. Archived prior ops docs in `docs/archive/ops/`.
- **Monorepo** — `docs/monorepo/plan.md` (combined current state + blueprint + prep).
- **HCI** — `docs/hci/hci_spec.md` (merged spec/calibration/ranking/context).
- **Host/Chat** — `docs/host_chat/frontend_contracts.md` (canonical), `host_response_schema.md`, `host_chat_behavior.md`, `http_stub.md`, stubs/env artifacts.
- **Lyrics** — `docs/lyrics/overview.md` (pipeline + contract), archives in `docs/archive/lyrics/`.
- **Calibration/Norms** — `docs/calibration/` (audio calibration, tempo confidence, post-checklist), `docs/norms/market_norms.md` (build/runbook; archives in `docs/archive/norms/`).
- **Pipelines/Spines** — `docs/pipeline/`, `docs/spine/` (with README), `docs/historical_spine/`, `docs/ttc/`.
- **Research** — `docs/research/` (CIF — Creative Intelligence Framework — tech whitepaper v1.2, exec summaries, plain-English summaries, historical echo/methods); superseded PDFs/addenda live in `docs/archive/research/`. See `docs/research/CIF_Index.md` for the quick index.
- **Integrations** — `docs/integrations/macos.md`, `ACOUSTICBRAINZ_INTEGRATION.md`; archives in `docs/archive/integrations/`.
- **Samples** — `docs/samples/` (+ README for payload descriptions).
- **Plans** — `docs/plans/TIER3_PLAN.md` (Tier 3 spine/echo expansion).
- **Schemas/UI** — `docs/schemas/pack_readme.md` (JSON Schemas for artifacts, host response); host UI mock: `docs/host_chat/ui_mock/mock1.md`.
- **Spine/TTC Quickstart** — `docs/ops/spine_ttc_quickstart.md` (fast commands + outputs).
- **CI** — `docs/ci.md` (workflow summary).
- **Quick commands (shortlist)** — `make quick-check` (or `infra/scripts/quick_check.sh`); `automator.sh <audio>` for the 11-file payload (adds `<stem>.tempo_norms.json` + tempo overlay in `.client.rich.txt`); `python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json` for data/public bootstrap.
- **Isolation/headless smokes** — every major component (chat/host, sidecars/pipeline, engines) has env/flag knobs and headless smokes for sparse pulls. See `docs/COMMANDS.md` and `docs/Makefile.sparse-smoke` for `sparse-smoke-all` and per-component commands.
- **Component READMEs** — engines (`engines/*/README.md`), sidecars (`tools/sidecars/README.md`), chat backend (`tools/chat/README.md`), pipeline quickstart (`docs/pipeline/README.md`) give per-folder install/smoke/test steps for targeted pulls.
- **Compliance** — root `NOTICE`, MIT LICENSE files in shared/config; SBOM helper in `docs/sbom/` (`make sbom`) and CI workflows for smokes and pip-audit.
- **UI open-source notice snippet** — `docs/ui_open_source_notices_snippet.txt` for embedding in app UI/legal screens.

See `docs/archive/` for prior snapshots of merged docs (architecture, monorepo, ops commands, host chat, HCI, research PDFs) and `docs/archive/gpt_playbooks/` for legacy GPT playbooks/briefs.

Data hygiene: the `data/` directory is kept for local inputs/exports but its contents are git-ignored; prefer small samples + README if versioning any datasets.

Pipeline fixtures: see `tests/fixtures/pipeline_sample/` for synthetic “success” shapes (payload → advisory → host response) and `tests/test_pipeline_fixture_shapes.py` for the sanity check.

Full-app smoke behavior: `make e2e-app-smoke` uses a temp dir (e.g., `/tmp/ma_e2e_xxxx`), generates `tone.wav`, runs the pipeline to `advisory.json`, runs the host CLI to `host_out.json`, then deletes the temp dir. No files are left in the repo tree.

Infra layout: orchestration assets live under `infra/scripts/` and `infra/docker/`; use these paths directly.

Calibration: lives under `shared/calibration/`; env `MA_CALIBRATION_ROOT` defaults to the new path.

Shared utilities: `shared/utils/` exists (currently re-exporting `shared.core`) to mirror the target monorepo layout.

Data scoping: `data/` is the base (contents git-ignored); use `data/public/` for shareable/bootstrap assets (spine, market_norms, lyric_intel if provided) and `data/private/` for local-only/sensitive/generated data. Outputs live under `data/features_output/`.

CI stub: `infra/scripts/ci_local.sh` runs the full quick check as a local/pre-CI runner.
CI workflow: `.github/workflows/ci.yml` runs the quick check on push/PR.
Data bootstrap: `infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json` to download assets into `data/` (fill manifest URLs/checksums).

- Data/bootstrap details: `docs/data_bootstrap.md` covers layout, S3/HTTPS bootstrap, and env overrides.
