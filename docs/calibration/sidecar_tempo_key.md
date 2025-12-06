# Tempo/Key Sidecar (Essentia/Madmom) — Notes

## At a glance

- Sidecar = external helper that runs alongside the extractor to produce tempo/beat/key metadata. This doc covers the extraction sidecar; overlay sidecars (tempo_norms/key_norms) live in `tools/tempo_norms_sidecar.py` / `tools/key_norms_sidecar.py` and are post-processing overlays on existing features/lanes.
- Backend order: Essentia → Madmom → librosa (auto fallback).
- Records: backend/detail/version, tempo/key/mode, raw+normalized confidences, beats count (full beats live in `.sidecar.json`), status/warnings.
- Default behavior: fallback keeps runs alive; optional `--require-sidecar` fails if sidecar isn’t used; warnings flag missing/invalid payloads.

## Who / What / Why / How / Where / When

- Who: Anyone running the MusicAdvisor pipeline who wants higher-accuracy tempo/beat/key info (Essentia/Madmom) feeding into injectors/rankers.
- What: A sidecar command (`tools/cli/tempo_sidecar_runner.py` – legacy shim at `tools/tempo_sidecar_runner.py`) that emits tempo/key/beat JSON; the main extractor ingests it when `--tempo-backend sidecar` is set.
- Why: Essentia/Madmom are stronger than the built-in librosa estimators; we normalize confidences to 0–1 for downstream compatibility while retaining raw values for transparency.
- How: The sidecar runs alongside extraction, writes a `.sidecar.json`, and the pipeline merges tempo/key/beat meta, recording backend/detail/version, raw/normalized confidence, and status/warnings. Fallback order: Essentia → Madmom → librosa.
- Where to start: Use Automator (already wired), or run `python3 tools/cli/ma_audio_features.py --audio song.wav --out song.features.json --tempo-backend sidecar --tempo-sidecar-json-out /tmp/tempo.json` (shim `tools/ma_audio_features.py` still works). Inspect the sibling `.sidecar.json` for full beats, check `tempo_backend_detail` for backend used.
- When: Use whenever you want sidecar tempo/key; add `--require-sidecar` if you prefer a hard failure over fallback. Re-run with `--force`/`--no-cache` when switching to sidecar to avoid stale fingerprints.
- Problem it solves: Improves tempo/key accuracy over built-in estimators and provides confidence/beat context for downstream scoring and guardrails, while keeping raw values for transparency.
- Why this approach is better: Leverages best-of-breed audio libraries (Essentia/Madmom) without changing core scoring defaults, normalizes confidences to a shared 0–1 scale for interoperability, and retains raw fields + warnings/strict mode for traceability and debugging.
- Confidence calibration defaults live in `adapters/confidence_adapter.py` and can be overridden via `config/tempo_confidence_bounds.json` (per-backend bounds/labels).
- Guardrail: `scripts/check_sidecar_deps.sh` should remain present and executable; tests enforce this to catch missing native deps early.

## What it does

- “Sidecar” = an external helper that runs alongside the main extractor to produce tempo/beat/key metadata, which we merge into the pipeline features.
- Adds an external tempo/beat/key sidecar to the pipeline extractor via `--tempo-backend sidecar` (default in Automator).
- Backend preference: **Essentia → Madmom → librosa**. Falls back automatically if a backend is missing or fails.
- Merges sidecar tempo/key/beat metadata into `.features.json` and records backend detail/version and source JSON path.

## Fields we record

- `tempo_backend` = `external`, `tempo_backend_detail` = backend name, `tempo_backend_meta` = {backend, backend_version}, `tempo_backend_source` = sidecar JSON path.
- Tempo confidence: `tempo_confidence_score_raw` (sidecar-native), `tempo_confidence_score` (normalized 0–1), `tempo_confidence` (label).
- Key confidence: `key_confidence_score_raw` (e.g., Essentia key strength), `key_confidence_score` (normalized 0–1).
- Beats: `tempo_beats_count` in `.features.json` (lean), full `beats_sec` available in `.sidecar.json`.
- Backend meta: backend/detail/version recorded when available.
- Optional extras: `tempo_alternates` (e.g., half/double from sidecar) and `key_candidates` (top candidates if provided).
- Optional diagnostics: `tempo_candidates` (primary + alternates with confidence if provided) for debugging tempo ambiguity.
- Core tempo/key/mode are replaced by the sidecar values when present; half/double tempos remain for reference.
- Status/flags: `sidecar_status` plus optional `sidecar_warnings` (e.g., sidecar missing/invalid, fallback to librosa, or missing backend version).

### Sidecar JSON contract (tempo)

- Output filename: `tempo.sidecar.json` (UTF-8 JSON, ≤ 5 MB).
- Required keys: `tempo_primary`, `tempo_alt_half` (nullable), `tempo_alt_double` (nullable), `tempo_confidence` (label), `tempo_confidence_score_raw` (float), `backend` (string), `backend_version` (string or null).
- Optional keys: `beats_sec` (array of floats), `mode`, `key`, `key_confidence_score_raw` (float), `tempo_candidates` (array), `tempo_alternates` (array), `tempo_backend_meta` (object).
- The adapter enforces max bytes and expects a top-level object; missing optional fields are tolerated and will be warned/trimmed.

### Sidecar JSON (annotated example)

```json
{
  "backend": "essentia",
  "backend_version": "2.1.0",
  "tempo_primary": 102.4,
  "tempo_alt_half": 51.2,
  "tempo_alt_double": 204.8,
  "tempo_confidence_score_raw": 3.1,
  "tempo_confidence": "high",
  "beats_sec": [0.45, 1.03, 1.61],
  "key": "D",
  "mode": "minor",
  "key_confidence_score_raw": 0.81
}
```

- `backend`/`backend_version` identify the sidecar.
- `tempo_primary` is the canonical tempo; `tempo_alt_half`/`tempo_alt_double` are kept for reference.
- `tempo_confidence_score_raw` is normalized by the adapter to 0–1 (`tempo_confidence_score` in features/merged).
- `beats_sec` are optional full beats (kept only in `.sidecar.json`); `tempo_beats_count` lives in `.features.json`.
- `key`/`mode`/`key_confidence_score_raw` mirror tempo fields for tonal info.

## Normalization rationale

- Downstream consumers (injectors/ranker/tempo weighting) expect 0–1 confidence. Essentia/Madmom scores are backend-specific and not standardized.
- We keep raw scores for transparency and also map to 0–1 for interoperability:
  - Essentia tempo confidence calibrated on `benchmark_set_v1_1` (p5≈0.93, p95≈3.64 → 0..1).
  - Key strength is clamped to 0–1.
- Raw fields remain alongside normalized values for diagnostics and future tuning.

## Why include / exclude certain data

Included (small footprint, scoring-relevant):

- Tempo, beats (+count), backend detail/version, raw + normalized tempo confidence.
- Key/mode, raw + normalized key strength.

Excluded (for now) to stay lean:

- Full key probability vectors, per-beat strength traces, heavy chroma/HPCP/timbre descriptors.
- Alternate tempo candidates from Essentia (current pipeline already carries half/double; can be added if needed).

## Caching note

Cache keys include the config fingerprint. If you switch to `--tempo-backend sidecar` but reuse old outputs, rerun with `--force` (or `--no-cache`) so the extractor recomputes with the sidecar and writes external metadata. A `cache_status: "miss"` only means “no matching cache entry” for that fingerprint—it does not guarantee the sidecar ran. Verify `tempo_backend_detail` shows `essentia`/`madmom` and that a `.sidecar.json` exists.

## Usage

- CLI: `python3 tools/cli/ma_audio_features.py --audio song.wav --out song.features.json --tempo-backend sidecar --tempo-sidecar-json-out /tmp/tempo.json [--tempo-sidecar-verbose]` (shim: `tools/ma_audio_features.py`)
- Automator: already wired to use the sidecar and save a sibling `.sidecar.json`.
- Sidecar runner (standalone): `python3 tools/cli/tempo_sidecar_runner.py --audio song.wav --out /tmp/tempo.json --backend auto --verbose` (shim: `tools/tempo_sidecar_runner.py`)

## Impact on scoring/QA

- Tempo/key values come from the sidecar when present; backend/source/meta recorded for transparency.
- Tempo confidence drives optional tempo down-weighting (`--use-tempo-confidence` flags in injectors/probe/ranker).
- QA/config fingerprints include the backend choice and sidecar command so runs are traceable.
- Scoring defaults do not change; the sidecar improves input accuracy and makes confidence/provenance visible. To let confidence affect scoring, enable `--use-tempo-confidence`.

## Caching note (strict mode)

Cache keys include the config fingerprint. If you switch to `--tempo-backend sidecar` but reuse old outputs, rerun with `--force` (or `--no-cache`) so the extractor recomputes with the sidecar and writes external metadata. A `cache_status: "miss"` only means “no matching cache entry” for that fingerprint—it does not guarantee the sidecar ran. Verify `tempo_backend_detail` shows `essentia`/`madmom` and that a `.sidecar.json` exists. Optional strict mode: add `--require-sidecar` to fail if the sidecar is not used (e.g., if it falls back to librosa). By default, the pipeline falls back to keep runs alive.
