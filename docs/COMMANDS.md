# CLI Entry Points

- Audio pipeline:
  - Canonical: `python -m ma_audio_engine.tools.pipeline_driver --help`
  - Shims: `ma-pipe`, `ma-extract`, `music-advisor-smoke` (thin wrappers to `ma_audio_engine`).
- Tempo norms + overlay:
- Generate tempo norms sidecar: `python3 tools/tempo_norms_sidecar.py --help` (writes `<stem>.tempo_norms.json`). Flags of note: `--adaptive-bin-width`, `--smoothing/--smoothing-method gaussian`, `--smoothing-sigma`, `--neighbor-steps/--neighbor-decay`, `--fold-low/--fold-high`, `--trim-lower-pct/--trim-upper-pct`, `--bpm-precision`. Payload includes `peak_clusters`, `hit_medium_percentile_band`, neighbor `weight/step`, and lane `shape` metrics.
- Generate key norms sidecar: `python3 tools/key_norms_sidecar.py --help` (writes `<stem>.key_norms.json`). Payload now includes lane_shape (entropy/flatness/mode_split), per-mode top keys, fifths_chain ordering, and weighted target moves with rationale_tags/chord_fit_hint; overlay legend: st=semitones delta; w=weight; c5=circle-of-fifths distance; tags=rationale tags.
- Host/chat loader helpers: `from tools.overlay_sidecar_loader import load_tempo_overlay_payload, load_key_overlay_payload` to load sidecars and get a chat/reco-friendly dict without recomputing stats.
- Chat router (now under `tools/chat/`): `from tools.chat import route_message, ChatSession, classify_intent, handle_intent` (rule-based intents for tempo/key/status; uses overlay dispatcher in `tools/chat/chat_overlay_dispatcher.py`); chat text helpers in `tools/chat/overlay_text_helpers.py`.
- Chat intents include help/legend/context and expanded coverage (tempo/key/neighbors/HCI/TTC/QA/status/metadata/lane summary/key targets/tempo targets/compare/why/artifacts) with filtering (top N, tier), keyword-scoring fallback, optional intent model hook, optional paraphrase hooks (`tools/chat/paraphrase.py`, env `CHAT_PARAPHRASE_ENABLED`), and length clamping; router supports summary/verbose toggles, caching, and truncated outputs for chat. Host remains a thin front door; optional delegation to `tools/chat` is controlled by `HOST_CHAT_BACKEND_MODE` (on/auto/off) and a provided `client_rich_path` in chat requests. For modular/sparse work: `git clone --filter=blob:none <repo> && cd music-advisor && git sparse-checkout init --cone && git sparse-checkout set hosts/advisor_host tools/chat shared`; then `pip install -e hosts/advisor_host -e tools/chat` (with `PYTHONPATH=.`), run `pytest hosts/advisor_host/tests`, and `python -m advisor_host.cli.http_stub` to smoke. Apply similar sparse patterns per major package (engines, pipelines, sidecars) to enable targeted pulls.
- Dynamic knobs reference: see `docs/engine_dynamic_knobs.md` for env toggles across host/chat and engines (audio, lyrics/STT, recommendation, TTC).
- Pipeline/sidecar knobs: see `docs/pipeline_dynamic_knobs.md` for sidecar adapter envs (`MA_TEMPO_SIDECAR_CMD`, `MA_SIDECAR_PLUGIN`, `ALLOW_CUSTOM_SIDECAR_CMD`), logging (`LOG_JSON`, `LOG_REDACT`), and overlay/feature extraction notes.
- Pipeline smokes for targeted pulls (with `PYTHONPATH=.`):
  - Tempo norms: `python tools/tempo_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-bpm 120 --out /tmp/demo.tempo_norms.json --overwrite`
  - Key norms: `python tools/key_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-key "C major" --out /tmp/demo.key_norms.json --overwrite`
  - TTC stub: `python tools/ttc_sidecar.py estimate --db /tmp/ttc.db --song-id demo --out /tmp/demo.ttc.json`
  - Sidecar adapter sanity: `python - <<'PY'\nfrom tools.sidecar_adapter import run_sidecar\npayload, out, warnings = run_sidecar('tone.wav', None, keep_temp=True)\nprint('ok', bool(payload) or warnings)\nPY`
- Shared libs install hint (to reduce PYTHONPATH hacks on sparse pulls): `pip install -e src/ma_config -e shared` (or `pip install -e .`) to make `ma_config` and `shared.*` available without manual PYTHONPATH tweaks; otherwise add `src`/`shared` to `PYTHONPATH=.` as documented in per-tool smokes. Packages are named `music-advisor-config` and `music-advisor-shared` for clarity.
- Makefile helpers (headless smokes): see `docs/Makefile.sparse-smoke` for `sparse-smoke-*` targets (chat/tempo/key/ttc/reco) using `PYTHONPATH=.`; intended for sparse/headless verification.
- `make -f docs/Makefile.sparse-smoke sparse-smoke-all` runs all smokes in one go.
- `make install-shared` installs shared/config packages locally.
- SBOM: `make sbom` (requires `cyclonedx-bom`); outputs `docs/sbom/sbom.json`. CI workflow `SBOM` (manual dispatch) can also generate and upload.
- Vulnerability scan: `make vuln-scan` (pip-audit, non-blocking). CI workflow `Vulnerability Scan` runs pip-audit on push/PR.

## Headless isolation quickstarts (step-by-step)

All flows assume `pip install -e src/ma_config -e shared` (or `pip install -e .`) and `PYTHONPATH=.` for local runs.

- Chat/host:

  1. Install: `pip install -e hosts/advisor_host -e tools/chat`.
  2. Smoke: `HOST_CHAT_BACKEND_MODE=on python -m advisor_host.cli.http_stub` and POST `/chat` with `{"message":"tempo?","client_rich_path":"/abs/path/to/song.client.rich.txt"}`. Fallback smoke: `cat sample.client.rich.txt | python -m advisor_host.cli.ma_host`.
  3. Tests: `pytest hosts/advisor_host/tests`.

- Tempo norms sidecar:

  1. Smoke: `python tools/tempo_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-bpm 120 --out /tmp/demo.tempo_norms.json --overwrite`.
  2. Adapter sanity: `python - <<'PY'\nfrom tools.sidecar_adapter import run_sidecar\npayload, out, warnings = run_sidecar('tone.wav', None, keep_temp=True)\nprint('ok', bool(payload) or warnings)\nPY`.
  3. Tests: (none dedicated; rely on smoke + downstream tests).

- Key norms sidecar:

  1. Smoke: `python tools/key_norms_sidecar.py --song-id demo --lane-id tier1__2015_2024 --song-key "C major" --out /tmp/demo.key_norms.json --overwrite`.
  2. Adapter sanity (same as tempo).
  3. Tests: (none dedicated; rely on smoke + downstream tests).

- TTC sidecar/engine:

  1. Smoke: `python tools/ttc_sidecar.py estimate --db /tmp/ttc.db --song-id demo --out /tmp/demo.ttc.json`.
  2. Optional remote check: set `TTC_ENGINE_MODE=remote`, `TTC_ENGINE_URL=<endpoint>` and rerun; should fail fast if URL missing.
  3. Tests: `pytest engines/ttc_engine/tests`.

- Recommendation engine:

  1. Smoke: `python - <<'PY'\nfrom recommendation_engine.engine.recommendation import compute_recommendation\nfrom recommendation_engine.tests.fixtures import sample_payload, sample_market_norms\nrec = compute_recommendation(sample_payload, sample_market_norms)\nprint('ok', bool(rec))\nPY`.
  2. Tests: `pytest engines/recommendation_engine/tests`.

- Audio engine:

  1. Smoke: `python tools/tempo_sidecar_runner.py --audio tone.wav --out /tmp/tone.tempo.json`.
  2. Tests: `pytest engines/audio_engine/tests` (if present) or run a targeted tool with `--help`.

- Lyrics/STT engine:
  1. Smoke: `python engines/lyrics_engine/tools/lyric_wip_pipeline.py --help` (or run an STT helper on a short clip).
  2. Tests: `pytest engines/lyrics_engine/tests` (if present).

Tip: all smokes can be invoked together via `make -f docs/Makefile.sparse-smoke sparse-smoke-all`.

- Inject overlays: `python3 tools/ma_add_tempo_overlay_to_client_rich.py --client-rich <path>` (tempo) and `python3 tools/ma_add_key_overlay_to_client_rich.py --client-rich <path>` (key); both are idempotent insertions.
- Pack writer:
  - Canonical: `python -m ma_audio_engine.tools.pack_writer --help`
  - Shim: `tools/pack_writer.py` imports the canonical code.
- Lyric WIP pipeline: `make lyrics-cli-help` (runs `engines/lyrics_engine/tools/lyric_wip_pipeline.py --help` with PYTHONPATH set).
- Host CLI: `make host-cli-help` (runs `hosts/advisor_host/cli/ma_host.py --help` with PYTHONPATH set).

Notes:

- Pipeline/pack tools live in `ma_audio_engine.tools.*`; `tools/` provides backward-compatible shims only.
- Avoid adding new sys.path hacks; rely on PYTHONPATH or `scripts/with_repo_env.sh`.
