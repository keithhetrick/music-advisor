# 🎧 Music Advisor — Local Audio → JSON Extractors

Status: ✅ Last verified with 11-file payload (tempo_norms sidecar + tempo overlay) + Automator echo inject.

Convert audio files **locally** into structured JSON for the Music Advisor ecosystem.  
**No cloud uploads • No NDA risk • No label leaks**

> 🎯 _Local audio → JSON → Music AI forecasting pipeline_

This repo now has **two** audio feature extractors:

1. **Canonical HCI / Pipeline Extractor**  
   `tools/cli/ma_audio_features.py` → flat `.features.json` used by HCI, axes, and calibration. (Legacy shim at `tools/ma_audio_features.py` still works.)

2. **Standalone / Client-Oriented Extractor**  
   `ma_audio_features.py` (root) → nested JSON (`flat` + `features_full`) for client ingestion and manual analysis. Helper files are emitted with the neutral token `client` (e.g., `.client.txt/.client.json/.client.rich.txt`).

They share the **same core logic** for tempo, loudness, energy, danceability, and valence, but emit **different JSON shapes** for different jobs.

---

## 🏷️ Badges

![Local Processing](https://img.shields.io/badge/Data-Local_Only-3DDC84?style=flat&logo=box)  
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)  
![Audio Processing](https://img.shields.io/badge/Audio-Librosa-orange?style=flat&logo=music)  
![Security](https://img.shields.io/badge/NDA_Safe-Yes-00C853?style=flat&logo=shieldcheck)  
![Status](https://img.shields.io/badge/Mode-Private_AI_A%26R-8E44AD?style=flat&logo=musicbrainz)

---

## 🔍 What It Extracts

Both extractors compute the same **core musical features**:

| Feature         | Description                                   |
| --------------- | --------------------------------------------- |
| 🎵 BPM          | Tempo detection (with half/double-time logic) |
| 🎼 Key & Mode   | Estimated root + major/minor mode             |
| ⏱️ Duration     | Track length (seconds)                        |
| 📉 Loudness     | Integrated LUFS (or RMS-based proxy)          |
| ⚡ Energy       | Dynamics / perceived intensity (0–1)          |
| 💃 Danceability | Groove, beat strength, regularity (0–1)       |
| 😊 Valence      | Emotional brightness / optimism (0–1)         |

> 🧠 For HCI scoring & calibration, **only the flat pipeline schema matters**.  
> For client prompts and “nice” structured payloads, the nested schema is more convenient. New helpers use the neutral `client` token; client helpers remain available as aliases.

### Outputs (current 11-file payload: adds tempo_norms sidecar + tempo overlay injection)

Automator/pipeline runs emit a consistent payload under `data/features_output/YYYY/MM/DD/<stem>/`:

- `<stem>_<ts>.features.json` (flat pipeline features; legacy `<stem>.features.json` may coexist)
- `<stem>.sidecar.json` (tempo/key sidecar; Automator keeps this non-timestamped)
- `<stem>.tempo_norms.json` (lane tempo norms + advisory; feeds the TEMPO LANE OVERLAY block in `.client.rich.txt`)
- `<stem>.key_norms.json` (lane key norms + advisory; feeds the KEY LANE OVERLAY block in `.client.rich.txt`)
- `<stem>_<ts>.merged.json`
- `<stem>_<ts>.hci.json`
- `<stem>_<ts>.ttc.json`
- `<stem>.neighbors.json`
- `<stem>.client.txt`
- `<stem>.client.json`
- `<stem>.client.rich.txt` (echo-injected rich payload with context header)
- `<stem>.client.rich.json`
- `run_summary.json` (paths/bytes for the run)

Tests/fixtures: see `tests/fixtures/pipeline_sample/` and `tests/test_pipeline_fixture_shapes.py` for a runnable shape check.

### Sidecar taxonomy (naming)

- **Extraction sidecars (aux extractors)**: tempo/key runner (Essentia/Madmom/librosa) writing `<stem>.sidecar.json`; lyric STT and TTC tools fall in the same “extractor” bucket. These read audio (or equivalent primaries) and produce core signals.
- **Overlay sidecars (post-processing overlays)**: `tempo_norms_sidecar.py` and `key_norms_sidecar.py` writing `<stem>.tempo_norms.json` / `<stem>.key_norms.json`; they consume already-extracted features/lanes and emit lane-aware advisory/overlay JSON.
- Filenames and schemas stay as-is; the taxonomy is documentation-only to keep roles clear without breaking artifacts.

### How to read the artifacts (annotated)

`<stem>_<ts>.merged.json` (truncated):

```json
{
  "source_audio": "/path/to/song.wav",
  "pipeline_version": "1.5.0",
  "feature_pipeline_meta": {
    "tempo_backend_detail": "essentia",
    "sidecar_status": "ok",
    "config_fingerprint": "sha256:...",
    "warnings": []
  },
  "features_full": {
    "bpm": 102.3,
    "duration_sec": 201.5,
    "loudness_lufs": -9.2,
    "energy": 0.71,
    "danceability": 0.68,
    "valence": 0.42
  },
  "axes": {
    "TempoFit": 0.83,
    "RuntimeFit": 0.78,
    "LoudnessFit": 0.74,
    "Energy": 0.71,
    "Danceability": 0.68,
    "Valence": 0.42
  }
}
```

- `feature_pipeline_meta` records provenance (backend, status, config hash, warnings).
- `features_full` holds the normalized feature values.
- `axes` are derived fits used by downstream HCI/recommendation; these must remain shape-stable.

### Engine audit/run summary (where they appear)

- **`run_summary.json`** sits next to client/HCI artifacts; it records timestamps, backends used, config fingerprints, warnings, and hashes for the run. Useful for quick provenance without opening the pack.
- **`engine_audit.json`** (full mode) captures deeper provenance (engine version, sidecar/backend status, artifacts present). Use it when debugging mismatches or confirming exact inputs to the app bundle.

### Engine audit (annotated example)

```json
{
  "engine_version": "1.5.0",
  "config_fingerprint": "sha256:...",
  "sidecar": { "backend": "essentia", "status": "ok" },
  "artifacts": [
    "foo_20251201_010203.features.json",
    "foo_20251201_010203.sidecar.json",
    "foo_20251201_010203.merged.json",
    "foo_20251201_010203.pack.json",
    "foo.hci.json",
    "foo.neighbors.json"
  ],
  "warnings": [],
  "generated_at": "2025-12-01T00:00:00Z"
}
```

- `engine_version` + `config_fingerprint` anchor provenance.
- `sidecar` shows which backend actually ran and its status.
- `artifacts` lists what was produced; missing entries signal failures.
- `warnings` surfaces degraded paths (fallbacks, missing norms, etc.).

### Run summary (annotated example)

```json
{
  "audio_hash": "sha256:...",
  "pipeline_version": "1.5.0",
  "config_fingerprint": "sha256:...",
  "sidecar_status": "ok",
  "tempo_backend_detail": "essentia",
  "warnings": [],
  "timestamps": {
    "started_at": "2025-12-01T00:00:00Z",
    "finished_at": "2025-12-01T00:00:45Z"
  }
}
```

- Quick per-run provenance that sits with `.client.*`/`.hci.json`.
- Use `audio_hash` to detect stale/duplicate runs; `timestamps` for duration.

#### Run summary fields (quick ref)

- `audio_hash` — hash of input audio (detects stale/duplicates).
- `pipeline_version` — extractor/pipeline version used.
- `config_fingerprint` — hash of config/profiles/flags.
- `sidecar_status` / `tempo_backend_detail` — which backend ran and its health.
- `warnings` — degraded/fallback notes.
- `timestamps.started_at` / `finished_at` — ISO times for duration.

| Field                    | Meaning                                         |
| ------------------------ | ----------------------------------------------- |
| `audio_hash`             | Hash of input audio                             |
| `pipeline_version`       | Extractor/pipeline version                      |
| `config_fingerprint`     | Hash of config/profiles/flags                   |
| `sidecar_status`         | Sidecar health (`ok`/`fallback`/`missing`)      |
| `tempo_backend_detail`   | Backend actually used (essentia/madmom/librosa) |
| `warnings`               | Degraded/fallback notes                         |
| `timestamps.started_at`  | ISO start time                                  |
| `timestamps.finished_at` | ISO end time                                    |

Schema: `docs/schemas/run_summary.schema.json`.

### Visual checklist (per run)

```bash
features.json + sidecar.json
   ✓ tempo_backend_detail set
   ✓ sidecar_status ok
merged.json
   ✓ features_full present
   ✓ axes populated
run_summary.json
   ✓ audio_hash present
   ✓ warnings empty (or noted)
pack.json (full) / engine_audit.json
   ✓ artifacts listed, warnings empty
client.rich.txt / hci.json / neighbors.json
   ✓ present if HCI ran (hci-only/full)
```

---

## 📁 Folder Layout (High Level)

```bash
music-advisor/
├── .venv/                         # Virtual environment
├── ma_audio_features.py           # Standalone / Client extractor (nested JSON)
├── tools/
│   ├── cli/                       # Primary CLIs (preferred)
│   │   ├── ma_audio_features.py   # Canonical HCI / pipeline extractor (flat JSON)
│   │   ├── cli/tempo_sidecar_runner.py# Sidecar runner (Essentia/Madmom/librosa; shim at tools/tempo_sidecar_runner.py)
│   │   └── ...                    # Injectors/ranker/backfill
│   └── ma_audio_features.py       # Legacy shim that forwards to tools/cli/ma_audio_features.py
├── README_ma_audio_features.md    # This file
└── features_output/               # JSON exports (by date/project)
```

---

## ⚙️ Install

### 🍎 macOS / 🐧 Linux

```bash
mkdir -p ~/music-advisor/features_output
cd ~/music-advisor

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip
pip install librosa soundfile numpy pyloudnorm
```

### 🪟 Windows PowerShell

```powershell
mkdir $HOME\music-advisor\features_output
cd $HOME\music-advisor

python -m venv .venv
.\.venv\Scripts\activate

python -m pip install --upgrade pip
pip install librosa soundfile numpy pyloudnorm
```

Verify:

```bash
python -c "import librosa, soundfile, numpy, pyloudnorm; print('✅ Audio tools ready')"
```

### 🔧 Quick smoke (creates dated folder under features_output)

```bash
python tools/cli/ma_audio_features.py --audio tone.wav --out features_output/tone.features.json
# (Legacy shim: tools/ma_audio_features.py)
```

Expect `*.features.json` in `features_output/YYYY/MM/DD/<stem>/` with tempo/key/runtime/loudness/axes fields populated.

---

## 🧠 Which Extractor Should I Use?

### ✅ For HCI / Axes / Calibration / Benchmarking

Use **`tools/cli/ma_audio_features.py`** (shim: `tools/ma_audio_features.py`). This is the **canonical pipeline extractor**.  
Anything that feeds **HCI or `ma_benchmark_check.py`** should use this output.

**CLI example:**

```bash
cd ~/music-advisor
source .venv/bin/activate

python tools/cli/ma_audio_features.py \
  --audio "/path/to/song.wav" \
  --out   "features_output/2025/11/15/Benchmark_Set/song.features.json"
```

**Output shape (flat, pipeline-style):**

```json
{
  "source_audio": "/abs/path/to/song.wav",
  "sample_rate": 44100,
  "duration_sec": 201.23,
  "tempo_bpm": 123.0,
  "key": "D",
  "mode": "minor",
  "loudness_LUFS": -10.5,
  "energy": 0.78,
  "danceability": 0.82,
  "valence": 0.55
}
```

---

## 🧭 End-to-end pipeline (hci-only vs. full)

**HCI-only (default in Automator/Quick Action):**

```text
audio -> ma_audio_features.py (sidecar)     -> <ts>.features.json + <ts>.sidecar.json
      -> equilibrium_merge.py               -> <ts>.merged.json
      -> pack_writer.py (--no-pack)         -> client helper payloads (.client.txt/.json)
      -> tempo_norms_sidecar.py             -> <stem>.tempo_norms.json
      -> ma_hci_builder.sh + tempo/key overlays  -> .client.rich.txt (with TEMPO + KEY overlays) + .hci.json + .neighbors.json + run_summary.json
```

**Full pipeline (pack + engine audit):**

```text
audio -> ma_audio_features.py (sidecar)     -> <ts>.features.json + <ts>.sidecar.json
      -> equilibrium_merge.py               -> <ts>.merged.json
      -> pack_writer.py                     -> <ts>.pack.json + client helper payloads
      -> run_full_pipeline.sh               -> engine_audit.json
      -> tempo_norms_sidecar.py             -> <stem>.tempo_norms.json
      -> ma_hci_builder.sh + tempo/key overlays  -> .client.rich.txt (with TEMPO + KEY overlays) + .hci.json + .neighbors.json + run_summary.json
```

Artifacts are timestamped except compatibility copies (`.client.*`, `.hci.json`, `.neighbors.json`, `run_summary.json`).

---

## 📦 Payload schemas (high-level)

- **features.json** (flat): tempo/key/mode/loudness/energy/danceability/valence, config fingerprints, tempo_backend_detail/meta, tempo/key confidence, beats count.
- **sidecar.json**: tempo_primary/alt/half/double, tempo_confidence_score_raw, normalized tempo_confidence_score, key/mode, beats_sec (full), backend/meta/version, status/warnings.
- **merged.json**: normalized internal schema for pack/HCI; carries feature_pipeline_meta and sidecar provenance.
- **pack.json** (full mode): pack manifest + helper payloads.
- **client helpers:** `.client.txt/.json/.rich.txt`, `.hci.json`, `.neighbors.json`, `run_summary.json`.

Schemas are enforced via `tools/validate_io.py` and `schemas/`; see `docs/EXTRACT_PAYLOADS.md` for field references.

---

## 🛰️ Sidecar notes (Essentia/Madmom/librosa)

- Default sidecar command: `tools/cli/tempo_sidecar_runner.py` (prefers Essentia → Madmom → librosa).
- Configure via `--tempo-backend sidecar` and optional `--tempo-sidecar-cmd`/`--tempo-sidecar-json-out`; `--require-sidecar` to hard-fail on fallback.
- Provenance: `tempo_backend_detail`, `tempo_backend_meta`, `tempo_backend_source`, `sidecar_status`, `sidecar_warnings`.
- Confidence: raw score retained; normalized 0–1 via `adapters/confidence_adapter.py`; labels derived from raw when available.
- Safety: `tools/sidecar_adapter.py` enforces allowed binaries/placeholder checks, JSON size caps, timeouts; returns warnings instead of crashing pipelines.
- Tempo norms: `tools/tempo_norms_sidecar.py` emits `<stem>.tempo_norms.json` (lane stats + advisory) and feeds `tools/ma_add_tempo_overlay_to_client_rich.py`, which injects the TEMPO LANE OVERLAY (BPM) block into `.client.rich.txt` without altering other sections. Schema: `tools/tempo_norms_schema.json`; helper logic: `tools/tempo_relationships.py`. Flags of note: `--adaptive-bin-width` (Freedman–Diaconis with min/max guards), `--smoothing/--smoothing-method gaussian`, `--smoothing-sigma`, `--trim-lower-pct/--trim-upper-pct`, `--fold-low/--fold-high` (halftime/doubletime folding), `--neighbor-steps/--neighbor-decay`, and `--bpm-precision`. Sidecar now also exposes `peak_clusters`, `hit_medium_percentile_band`, neighbor `weight/step`, and `shape` metrics (skew/kurtosis/entropy); the overlay can optionally surface these fields when present.
- Key norms: `tools/key_norms_sidecar.py` emits `<stem>.key_norms.json` (lane key stats + advisory) and feeds `tools/ma_add_key_overlay_to_client_rich.py`, which injects the KEY LANE OVERLAY block into `.client.rich.txt` without altering other sections. Schema: `tools/key_norms_schema.json`; helper logic: `tools/key_relationships.py` (preferred enharmonic names, relative/parallel/fifths matrix, neighbor weights, chord-friendly key families). CLI flags include `--prefer-flat`, overlay display style, and schema validation; payload adds `lane_percent`, lane_shape (entropy/flatness/mode_split), per-mode top keys, fifths_chain ordering, and weighted target moves with rationale_tags/chord_fit_hint for historical-hit alignment. Overlay legend clarifies abbreviations: st=semitones delta; w=weight; c5=circle-of-fifths distance; tags=rationale tags.
- Host/chat helpers: `tools/overlay_sidecar_loader.py` can be imported to load tempo/key sidecars into chat/recommendation-friendly dicts without recomputing stats.

---

## 🛠️ Operational guidance

- **Validate**: `python tools/validate_io.py --root <out_dir>` post-run; schemas in `schemas/`.
- **Debug**: missing artifacts hint at failing step (features/merge/pack/HCI); see `docs/DEBUGGING.md` for failure modes and rerun tips (`--skip-hci-builder`, `--skip-neighbors`, `--mode full`).
- **Preflight**: ensure `infra/scripts/check_sidecar_deps.sh` is present/executable; Automator enforces venv sanity + pinned deps.
- **Logging hygiene**: set `LOG_JSON=1` for structured logs; `LOG_REDACT=1`/`LOG_REDACT_VALUES=...` to scrub secrets; `LOG_SANDBOX=1` to drop beats/neighbors in logs.
- **Cache control**: `CACHE_BACKEND=noop` or `--cache-backend noop` to avoid disk writes; defaults from `config/cache.json`.
- **QA policies**: `QA_POLICY=default|strict|lenient` or `--qa-policy` to align thresholds across extractor/injectors/ranker.

This schema is consumed by:

- `tools/ma_simple_hci_from_features.py`
- `tools/ma_benchmark_check.py`
- HCI axes + calibration tools
- Automator / drag-and-drop flows

> ⚠️ **Do not change these keys or semantics** without updating all HCI consumers.
> This is the one true format for `.features.json` in the pipeline.

---

## 🛰️ External tempo/key sidecars (Essentia/Madmom)

“Sidecar” here means an external helper process/artifact that runs alongside the main extractor to produce tempo/beat/key metadata, which we then merge into the pipeline features.

You can feed an external tempo/key/beat sidecar (Essentia or Madmom) into the pipeline extractor:

```bash
python tools/cli/ma_audio_features.py \
  --audio song.wav \
  --out song.features.json \
  --tempo-backend sidecar \
  --tempo-sidecar-json-out /tmp/tempo.json \
  --tempo-sidecar-verbose
```

Defaults run `tools/cli/tempo_sidecar_runner.py` (prefers Essentia → Madmom → librosa; shim: `tools/tempo_sidecar_runner.py`). The extractor merges the payload and records:

- `tempo_backend=external`, `tempo_backend_source=<sidecar json>`, `tempo_backend_detail=<essentia|madmom|librosa>`
- `tempo_backend_meta` (backend + version), `tempo_beats_sec`/`tempo_beats_count`
- `tempo_confidence_score_raw` (sidecar’s native value) plus a normalized `tempo_confidence_score` in the 0–1 band used across our pipeline
- `tempo_beats_count` (full `beats_sec` stays in `.sidecar.json`), `key_confidence_score_raw` (e.g., Essentia key strength), and a normalized `key_confidence_score`
- `sidecar_status` + optional `sidecar_warnings` when a sidecar is requested but missing/invalid or when we fall back to librosa
- A hardened sidecar adapter/bridge (`tools/sidecar_adapter.py`) is the only connection point: it validates `{audio}/{out}` templates, respects the custom-command allowlist, caps JSON size, and returns warnings without coupling pipeline internals to sidecar code. This keeps the pipeline loosely coupled and lets us swap/disable a backend without touching the extractor.
- A confidence adapter (`adapters/confidence_adapter.py`) normalizes external tempo confidence into 0–1 using bounds or backend heuristics; labels fall back to that normalized score.
- Modular adapters now in the extractor: QA policy loader (`adapters/qa_policy_adapter.py`), config fingerprint builder (`adapters/config_adapter.py`), logging shim (`adapters/logging_adapter.py`), backend registry (`adapters/backend_registry_adapter.py`). They keep QA thresholds, config assembly, logging, and backend wiring loosely coupled so we can extend/swap without touching core logic.
- Optional config overrides: drop a `config/qa_policy.json` (per-policy thresholds) or `config/logging.json` (prefix/redaction/secrets) to change behavior without code edits. Backend registry and tempo confidence also read optional config files in `config/`. Cache defaults can be set with `config/cache.json` (`default_cache_dir`, `default_backend`).
- Audio loader is adapterized (`adapters/audio_loader_adapter.py`); you can point to a different backend or mono setting via optional `config/audio_loader.json` without changing code.
- Neighbor adapter writes `*.neighbors.json` with schema/size guards (filters invalid rows, caps length, soft-truncates with warnings).
- Optional diagnostics: `tempo_candidates` (primary + alt tempos with confidence if provided) to aid in debugging tempo ambiguity; ranker flag `--show-sidecar-meta` can expose backend/confidence in summaries (off by default).
- Optional extras: `tempo_alternates` (from sidecar, e.g., half/double) and `key_candidates` (top candidates if provided by the sidecar)
- Optional diagnostics: `tempo_candidates` (primary + alt tempos with confidence if provided) to aid in debugging tempo ambiguity.
- Future modular adapters (on the roadmap): QA policy adapter (strict vs. lenient clipping/silence rules) and further cache/neighbor adapters to keep loose coupling as the app grows.
- Future expansion (modular/adapter mindset):
  - Cache adapter: pluggable cache backends (disk/mem/noop), consistent error handling, swap/disable without touching pipeline code.
  - QA policy adapter: map `QA_POLICY` presets to thresholds/actions (warn/fail/pass) so policies evolve independently from pipeline logic.
  - Sidecar command adapter: extend allowlist/denylist, sandbox modes, env overrides; pipeline remains oblivious to shell details.
  - Ranker I/O adapter: normalize neighbor/HCI read/write with schema guards/truncation; decouple ranker logic from file formats.
- Logging/telemetry adapter: centralized levels, redaction, diagnostics toggles; easy to silence verbose sidecar logs in production.
- Logging redaction toggles: set `LOG_REDACT=1` and optionally `LOG_REDACT_VALUES=secret1,secret2` to scrub sensitive strings from logs (applies to extractor + injectors + ranker). CLI mirrors this via `--log-redact` and `--log-redact-values "a,b,c"` on the extractor, `ma_add_echo_to_hci_v1.py`, `ma_add_echo_to_client_rich_v1.py`, and `hci_rank_from_folder.py`.
- QA handling presets in injectors: `--qa-policy strict` (client.rich/hci injectors) skips files whose feature QA gate is not pass/ok; default/lenient keep current behavior.
- Config adapter: single place for env/CLI/default loading/validation, passing typed config into pipeline/injectors/ranker.
- Backend registry: track available tempo/key backends (Essentia/Madmom/Librosa), priority, and capabilities; pipeline just asks for “best backend” without hardcoding order.
- Configurable adapters (data-first, optional):
  - `config/backend_registry.json` (if present) overrides supported backends and default sidecar command (else code defaults).
  - `config/tempo_confidence_bounds.json` (if present) overrides per-backend tempo confidence bounds/labels used by the confidence adapter (else calibrated defaults are used).

Modularity status (swap-readiness)

- Sidecar adapter bridge: `sidecar_adapter` + `backend_registry_adapter` isolate sidecar execution; swap a backend or command without touching extractor logic.
- Confidence normalization: `confidence_adapter` maps native backend scores to 0–1; bounds live in one place.
- Logging: `logging_adapter` with redaction is used by extractor, injectors, and ranker; toggled via env/CLI.
- QA/config: `qa_policy_adapter` and `config_adapter` centralize thresholds and fingerprints; policies can be changed without editing pipeline code.
- Cache: `cache_adapter` wraps on-disk cache; already in use by extractor (can be swapped for noop/mem later).
- Cache backend is selectable at runtime: `--cache-backend disk|noop` (or `CACHE_BACKEND` env) to disable cache reads/writes without changing other flags.
- Neighbors: `neighbor_adapter` guards schema/size; injectors trim inline neighbors and write full payloads to `.neighbors.json`.
- Service registry: `adapters/service_registry.py` exposes `get_logger/get_cache/get_qa_policy/get_exporter` and sandbox helpers so tools pull dependencies from one place instead of wiring instances manually.
- Logging sandbox: enable via `LOG_SANDBOX=1` or extractor `--log-sandbox` to scrub heavy/sensitive fields (beats, neighbors, hashes) before emitting debug logs; scrub rules live in `logging_adapter`.
- Backend registry adapter: `backend_registry_adapter` + `sidecar_adapter` form the adapter bridge between pipeline and sidecars; tweak `config/backend_registry.json` to enable/disable backends or change the default sidecar command without touching code.
  Remaining low-risk hardening (future)
- Pluggable QA policies for injectors/ranker (shared presets).
- Swappable cache backend (disk/mem/noop) via `cache_adapter` in ancillary tools.
- Light I/O adapters for ranker/injectors to further decouple file formats (optional).

Outside the extractor/ranker, the same adapter mindset can strengthen automation:

- Automators/batch scripts: wrap env/CLI assembly so changing flags or allowlists doesn’t require shell rewrites.
- Central config adapter: merge defaults + env + CLI once, validate, and hand typed config to tools.
- Logging/redaction adapter: one place to set levels, redact paths/hashes, toggle verbose diagnostics per mode (dev/prod/sandbox).
- File I/O adapters for injectors: read/write `.client.rich.txt` / `.hci.json` with schema guards/truncation to decouple injector logic from file format quirks.
- Security/sandbox policy: enforce allowlists (e.g., disallow custom sidecar commands unless explicitly enabled) via a runtime policy adapter instead of per-script checks.
- Testing/fixtures adapter: swap real vs. synthetic inputs/outputs for pipeline/sidecar/injectors without altering test harnesses.

Note on the vendor “host”/client builder layer:

- If it stays dumb (just loads templates and passes data through), heavy modularization isn’t required.
- Keep a minimal public interface (e.g., `build(prompt_cfg, data) -> str`) and separate concerns: template registry, upstream data shaping, downstream transport/config. A light interface + separation protects you if the host ever needs to grow beyond simple string assembly.

QA policy selection (env): `QA_POLICY=default|strict|lenient` can adjust clipping/silence thresholds without code changes; defaults match current behavior.

Why normalize to 0–1? All downstream consumers (injectors/ranker/tempo down-weighting) already expect 0–1 confidence, and that convention is widely used (probability-like scores, Spotify-style fields). Essentia/Madmom confidences are backend-specific and not standardized, so we keep the raw values for transparency and also map into 0–1 for interoperability. The current Essentia mapping is calibrated on `benchmark_set_v1_1` (p5≈0.93, p95≈3.64 → mapped to 0..1); we can tune it further if a different corpus suggests new bounds.

Backend versions: when available from the sidecar runtime, `tempo_backend_meta.backend_version` is populated; a warning is emitted only if the backend name is known but no version string is exposed.

### 🎯 Sidecar data: what’s included vs excluded (and why)

Available from Essentia/Madmom:

- Tempo + beat grid, tempo confidence (backend-specific), backend/version
- Key/mode + key “strength” (Essentia), key probabilities (full 12×2), alternate tempo candidates (Essentia)
- Beat-level details (per-beat strengths), chroma/HPCP, other descriptors

Included (lean, scoring-relevant):

- Tempo, beats (+count), backend/detail/version: core rhythm context
- Raw + normalized tempo confidence: enables tempo weighting; normalized to 0–1 for compatibility, raw retained for transparency/calibration
- Key/mode + key strength (raw + normalized): supports key confidence weighting
- Tempo alternates (half/double) and top tempo/key candidates when provided: useful for debugging ambiguity and traceability without bloating the main payload

Excluded (for now) to stay lean and avoid payload bloat:

- Full key probability vectors and per-beat strength traces: useful for deep diagnostics but not required for current scoring; can be added later if needed
- Heavy feature blobs (chroma/HPCP/timbre descriptors): outside the current goal (tempo/key/beat confidence for echo/ranker) and would inflate payloads

Rationale: keep the sidecar payload aligned with what downstream scoring/guardrails actually use (tempo/key/confidence/beat context), retain raw fields for transparency, and normalize to 0–1 where interoperability matters. Add heavier diagnostics only if/when a concrete scoring use case appears.

Backend preference hierarchy:

1. Essentia (if installed and succeeds)
2. Madmom (fallback)
3. librosa (final fallback)

### 🔄 Caching note

Cache keys include the config fingerprint. If you switch to `--tempo-backend sidecar` but reuse old outputs, rerun with `--force` (or `--no-cache`) so the extractor recomputes with the sidecar and writes external metadata. A `cache_status: "miss"` only means “no matching cache entry” for that fingerprint—it does not guarantee the sidecar ran. Verify `tempo_backend_detail` shows `essentia`/`madmom` and that a `.sidecar.json` exists.
Optional strict mode: add `--require-sidecar` to fail if the sidecar is not used (e.g., if it falls back to librosa). By default, the pipeline falls back to keep runs alive. When sidecar parsing fails or required fields are missing, `sidecar_warnings` will be populated to flag the condition.

Operational tips:

- Before large backfills, clear stale cache entries to save disk and ensure fresh runs: `infra/scripts/clear_feature_cache.sh` (prompts before deleting).

### ⚙️ Automator/env knobs (defaults)

- `FAIL_ON_CLIP_DBFS` (default: disabled in Automator; set to e.g., `-0.5` to hard-fail on extreme clipping). Mild clipping remains warn-only. A GUI toggle is planned for the macOS app.
- `TEMPO_CONF_LOWER` / `TEMPO_CONF_UPPER` (Automator default `0.9` / `3.6`): Essentia tempo confidence normalization window passed to the sidecar. Override if you calibrate on a new corpus.
- `MA_SIDECAR_CMD` (optional): override the sidecar command template (`{audio}` / `{out}` placeholders required).
- Dependency preflight: `infra/scripts/check_sidecar_deps.sh` verifies NumPy<2, Essentia import, optional Madmom; Automator runs it if present.
- Beats payload control: `infra/scripts/run_extract_strict.sh` defaults to `--tempo-sidecar-drop-beats` to keep sidecar payloads lean; pass `--keep-beats` if you need full `beats_sec`. Automator/guardrail paths keep beats by default.
- Sandbox log scrub: `--log-sandbox` (or `LOG_SANDBOX=1`) drops beats/neighbors from logged payloads and truncates long strings; meant for sandboxed runs.
- QA presets: `--qa-policy strict` (tighter silence/low-level) or `--qa-policy lenient`.
- Backend registry: `config/backend_registry.json` lets you enable/disable Essentia/Madmom/librosa/auto and set per-backend options (e.g., `tempo_confidence_bounds`). Disabled backends are skipped (or hard-fail if `--require-sidecar`); when using the default sidecar command we bias to the first enabled backend (Essentia → Madmom → librosa).
- Automator extraction runs fresh by default (`--no-cache --force`) to guarantee sidecar usage and updated metadata.
- If a sidecar fails, you’ll see `sidecar_status` and `sidecar_warnings` in `.features.json` and in the ranker QA summary (`--summarize-qa`). Fix the underlying install (Essentia/Madmom) or rerun with `--force`.
- For new corpora, recalibrate confidence normalization (e.g., compute p5/p95 of `tempo_confidence_score_raw` on your benchmark set and adjust mapping in `tools/cli/tempo_sidecar_runner.py`). Keep raw + normalized values for transparency while tuning.
  - See `docs/tempo_conf_calibration.md` for a repeatable Essentia/Madmom sweep + percentile workflow on `benchmark_set_v1_1`.
  - You can also run a librosa-only baseline on the same set (see the doc) to compare all three backends side by side.
- Current calibrated defaults (benchmark_set_v1_1):
  - Essentia: normalize with lower=0.93, upper=3.63; labels low<1.10, med 1.10–3.20, high>3.20.
  - Madmom: normalize with lower=0.21, upper=0.38; labels low<0.23, med 0.23–0.33, high>0.33.
  - Librosa: normalize with lower=0.92, upper=0.97 (optional); labels low<0.93, med 0.93–0.95, high>0.95.
- Low-confidence half/double resolver: when backend is madmom/librosa and confidence is low (<~0.30, tempo <80 or >180), the pipeline will try half/double tempos and keep the one with higher internal confidence (`tempo_choice_reason` will include `auto_half_double_adjust` if it switches).

Example (sidecar-backed excerpt):

```json
{
  "tempo_backend": "external",
  "tempo_backend_detail": "essentia",
  "tempo_backend_source": "…/track.sidecar.json",
  "tempo_confidence_score_raw": 2.7,
  "tempo_confidence_score": 0.67,
  "tempo_beats_count": 849,
  "sidecar_status": "used",
  "sidecar_warnings": ["sidecar_backend_version_missing"]
}
```

See the sibling `.sidecar.json` for the full beat grid and raw payload.

Who / What / Why / How / Where / When (quick guide):

- Who: Pipeline users who want higher-accuracy tempo/beat/key (Essentia/Madmom) flowing into injectors/ranker.
- What: An external sidecar runner (`tools/cli/tempo_sidecar_runner.py`; shim: `tools/tempo_sidecar_runner.py`) that outputs tempo/key/beat JSON; the extractor ingests it when `--tempo-backend sidecar` is used.
- Why: Essentia/Madmom outperform the built-in librosa estimators; we normalize confidences to 0–1 for compatibility and keep raw values for transparency.
- How: The sidecar runs alongside extraction, writes a `.sidecar.json`, and the extractor merges tempo/key/beat meta, recording backend/detail/version, raw+normalized confidence, and status/warnings. Fallback order: Essentia → Madmom → librosa.
- Where to start: Automator (already wired), or CLI: `python3 tools/cli/ma_audio_features.py --audio song.wav --out song.features.json --tempo-backend sidecar --tempo-sidecar-json-out /tmp/tempo.json --force` (shim at `tools/ma_audio_features.py`). Check `tempo_backend_detail` and the sibling `.sidecar.json`.
- When: Use whenever you want sidecar tempo/key; add `--require-sidecar` if you prefer failure over fallback; rerun with `--force`/`--no-cache` when switching to sidecar to avoid stale cache entries.
- Problem it solves: Improves tempo/key accuracy and provides confidence/beat context for downstream scoring and guardrails, while keeping raw values for transparency.
- Why this logic: We lean on best-of-breed backends, normalize confidences to a shared 0–1 scale for interoperability, and retain raw + warnings/strict mode for traceability/debugging without changing scoring defaults.
- Impact on scoring: Defaults stay unchanged; the sidecar improves inputs and makes confidence/provenance visible. To let confidence affect scoring, enable `--use-tempo-confidence`.

---

### 🎛️ For Client Ingest / Standalone Analysis / Pretty JSON

Use **root** `ma_audio_features.py`. It’s a richer, nested structure, perfect for:

- `/audio import { ... }` payloads
- Manual inspection in VS Code / Jupyter
- Human-readable snapshots outside the strict HCI flow

**CLI example:**

```bash
cd ~/music-advisor
source .venv/bin/activate

python ma_audio_features.py \
  "/path/to/song.wav" \
  -o "features_output/song_nested.features.json" \
  --title  "Song Title" \
  --artist "Artist Name" \
  --notes  "Optional notes"
```

**Output shape (nested, client-friendly):**

```json
{
  "path": "/abs/path/to/song.wav",
  "title": "Song Title",
  "artist": "Artist Name",
  "notes": "Optional notes",
  "source": "local",
  "flat": {
    "tempo_bpm": 123.0,
    "runtime_sec": 201.23,
    "loudness_lufs_integrated": -10.5,
    "key_root": "D",
    "key_mode": "minor",
    "energy": 0.78,
    "danceability": 0.82,
    "valence": 0.55
  },
  "features_full": {
    "bpm": 123.0,
    "mode": "minor",
    "key": "D",
    "duration_sec": 201.23,
    "loudness_lufs": -10.5,
    "energy": 0.78,
    "danceability": 0.82,
    "valence": 0.55
  }
}
```

> ⚠️ **This nested format is _not_ used by HCI directly.**
> If you feed it to HCI scripts, they won’t find the flat keys they expect.

---

## 🧪 Shape Validation & Legacy Conversion

### ✅ Validate a `.features.json` before HCI

Use the validator to make sure a file is in **pipeline shape**:

```bash
python tools/validate_features_shape.py \
  features_output/2025/11/15/Benchmark_Set/song.features.json
```

- Prints `OK (pipeline features shape)` if valid.
- If it detects a nested ROOT-style file, you’ll see a clear warning telling you to:
  - Re-extract with `tools/cli/ma_audio_features.py` (shim: `tools/ma_audio_features.py`), or
  - Convert using the helper script.

### 🔄 Optional: Convert ROOT → Pipeline

If you have older ROOT-style files and can’t easily re-run audio extraction:

```bash
python tools/convert_root_features.py \
  --in  "features_output/song_nested.features.json" \
  --out "features_output/song_pipeline.features.json"
```

For **benchmark / calibration sets**, the recommended approach is:

> Re-extract from the original audio with `tools/cli/ma_audio_features.py` (shim: `tools/ma_audio_features.py`)
> for maximum consistency and fewer moving parts.

---

## 🤖 Example Client Ingest Flow (using extracted features)

Once your pipeline has produced `.client.rich.txt` blocks (via your Automator / merger), a typical client flow looks like:

```bash
/audio import { ... }        # includes features_full + audio_axes + HCI_v1
/advisor ingest
/advisor run full
/advisor export summary
```

For **ad-hoc experiments** you can also:

```bash
# Simple manual JSON test (no audio)
python - << 'PY'
import json; print(json.dumps({
 "source":"manual","track_title":"Working Title","artist":"Artist",
 "features":{"bpm":100,"mode":"major","key":"A","duration_sec":176,
 "loudness_lufs":-8.5,"energy":0.78,"danceability":0.72,"valence":0.60}
}, indent=2))
PY
```

Paste into Client as:

```bash
/audio import { ... }
```

---

## 🧠 Activate Environment

### macOS / Linux (Activation)

```bash
cd ~/music-advisor
source .venv/bin/activate
```

### Windows (Activation)

```powershell
cd $HOME\music-advisor
.\.venv\Scripts\activate
```

Deactivate:

```bash
deactivate
```

---

## ⚡ Quick Launch Alias

### macOS / Linux (Alias)

```bash
echo 'alias maudio="cd ~/music-advisor && source .venv/bin/activate"' >> ~/.zshrc
```

Then:

```bash
maudio
```

### Windows PowerShell (Alias)

```powershell
Add-Content $PROFILE 'function maudio { cd "$HOME\music-advisor"; .\.venv\Scripts\activate }'
```

Then:

```powershell
maudio
```

---

## 🎤 Final Word

**Your audio never leaves your device.**
You now have:

- One **canonical** extractor for HCI, calibration, and benchmarking.
- One **Client-friendly** extractor for rich prompts and manual analysis.
- Guardrails to prevent shape collisions between the two worlds.

🚀 _Music Advisor — Always Private, Always Pro_
