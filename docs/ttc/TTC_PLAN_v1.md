# Time-To-Chorus (TTC) v1 — Integration Plan

## Purpose

- Add TTC as a first-class, spine-aligned sidecar that can be ingested alongside existing audio features (tempo/key/loudness/axes) without perturbing current scoring.
- Keep parity with existing sidecar patterns (Essentia/Madmom tempo/key, AcousticBrainz) and leave clear hooks for future lyric/structure engines.

### Why this matters

- TTC is a high-signal structural feature for modern guidance; keeping it as a sidecar preserves existing scoring while making structure visible to clients/hosts.
- A shared slug/track_id join lets audio + lyric/structure engines align on the same tracks without schema churn.

## Canonical keys and join surface

- Primary key: `tracks.slug` (present in spine lanes, feature filenames, and external feature tables). Also store `track_id` (FK to `tracks.id`) for joins.
- Scope: Tier 1–3 Historical Echo spine rows; reusable for ad-hoc/local feature runs by slug.

## TTC sidecar schema (proposed table `ttc_annotations_v1`)

- Identity: `id` PK, `track_id` FK → `tracks(id)`, `slug` UNIQUE.
- Core: `ttc_first_chorus_sec` REAL NOT NULL.
- Optionals: `ttc_first_chorus_beats` REAL, `ttc_first_chorus_bars` REAL, `ttc_ratio_runtime` REAL, `runtime_sec` REAL, `ttc_has_chorus` INTEGER (0/1), `ttc_confidence` REAL (0–1).
- Provenance: `ttc_source` TEXT enum (`billboard_corpus`, `harmonix`, `salami`, `annotated`, `estimated`), `ttc_method` TEXT (backend/version), `annotator` TEXT, `notes` TEXT, `created_at`, `updated_at`.
- JSON/CSV mirrors: `data/ttc/ttc_annotations_v1.csv` (slug + fields above) and/or `data/ttc/ttc_annotations_v1.jsonl` for lightweight ingest.
- Pattern reuse: mirror `features_external_acousticbrainz_v1` (slug + JSON blob) if we prefer a `features_external_ttc_v1` table with a `ttc_json` column instead of columns per field.

## Repository placement

- DDL/helper: `tools/ttc/ttc_schema.py` (ensure/drop `ttc_annotations_v1`, similar to `tools/db/acousticbrainz_schema.py`).
- Ingest/merge: `tools/ttc/ttc_corpus_ingest.py` (read corpora → CSV/DB), `tools/ttc/ttc_sidecar_builder.py` (merge multiple sources, validate).
- Docs: this file (`docs/ttc/TTC_PLAN_v1.md`).

## Integration hooks

- Extractors (audio):
  - `tools/cli/ma_audio_features.py` (flat pipeline; shim: `tools/ma_audio_features.py`): optionally read TTC sidecar (by slug) and populate the existing `TTC` block in `*.features.json` (`seconds`, `confidence`, `source`, etc.). No scoring changes.
- `ma_audio_features.py` (root/client): mirror TTC in `flat`/`features_full` if present.
  - Normalizers already expect TTC placeholders: `src/ma_audiotools/analyzers/audio_core.py`, `src/ma_audiotools/always_present.py`.
- Packs / client:
  - `tools/builder_cli.py` already accepts `ttc_sec`; keep passing through.
  - `.client.rich.txt` headers (`tools/ma_merge_client_and_hci.py`, `tools/hci/ma_add_echo_to_client_rich_v1.py`) can display TTC when `STRUCTURE_POLICY.use_ttc=true`.
  - Validator `tools/validator/verbose_validator.py` already knows `ttc_sec` and respects policy gates.
- Echo/HCI:
  - Historical Echo corpus builders (`tools/hci_v2_build_training_matrix.py`, `tools/hci_v2_build_targets.py`) can LEFT JOIN TTC for analytics/calibration (non-scoring at first).
  - Echo injectors (`tools/ma_add_echo_to_hci_v1.py`, `tools/hci/ma_add_echo_to_client_rich_v1.py`) can include TTC in the arrangement section for transparency.

## Alignment with existing sidecars (Essentia/Madmom)

- Follow the sidecar precedence used for tempo/key (`docs/sidecar_tempo_key.md`): keep TTC in a separate channel (`ttc_annotations_v1`), not mixed into tempo sidecar files.
- Provenance fields (`ttc_source`, `ttc_method`, `ttc_confidence`) mirror tempo sidecar metadata (`tempo_backend_detail`, confidence scores).
- Placement alongside existing sidecars under `data/` is safe; cache paths can mirror `features_external` if desired.

### Flow (ASCII)

```ascii
TTC corpora/dumps --> [ttc_annotations_v1 table/CSV/JSONL]
           |                         |
           +--> TTC sidecar lookup --+--> extractors emit TTC block in *.features.json
                                     |
                           packs/client.rich show TTC (gated)
                                     |
                      optional LEFT JOIN in echo/HCI analytics
```

### TTC fields (proposed)

- `ttc_first_chorus_sec` — primary TTC in seconds (required).
- `ttc_first_chorus_beats` / `ttc_first_chorus_bars` — optional beat/bar positions.
- `ttc_ratio_runtime` — TTC divided by runtime (optional).
- `runtime_sec` — optional runtime copy for joins.
- `ttc_has_chorus` — 0/1 flag if chorus exists.
- `ttc_confidence` — 0–1 confidence for the TTC value.
- `ttc_source` — `billboard_corpus|harmonix|salami|annotated|estimated|lyric_engine|...`.
- `ttc_method` — backend/version used (e.g., `ttc_rule_based_v1`).
- `annotator` / `notes` — optional provenance fields.
- `created_at` / `updated_at` — timestamps for audit.

Schema: `docs/schemas/ttc_annotations.schema.json`.

### Example TTC JSONL row (proposed)

```json
{
  "slug": "artist__title",
  "track_id": "abc123",
  "ttc_first_chorus_sec": 42.7,
  "ttc_first_chorus_beats": 16.0,
  "ttc_ratio_runtime": 0.22,
  "runtime_sec": 195.0,
  "ttc_has_chorus": 1,
  "ttc_confidence": 0.78,
  "ttc_source": "harmonix",
  "ttc_method": "ttc_rule_based_v1",
  "annotator": "human_annotator",
  "notes": "verified in DAW",
  "created_at": "2025-12-01T00:00:00Z",
  "updated_at": "2025-12-01T00:00:00Z"
}
```

## Lyric/structure engine alignment

- TTC is arrangement-level; future lyric engines (e.g., hook/first-vocal timing) can share the same slug/track_id join surface and extend this table (or a sibling `structure_annotations_v1`) with `time_to_first_vocal`, `intro_length_sec`, section labels.
- Keep TTC schema additive: additional columns/JSON keys can be added without breaking existing joins; `ttc_source` can include `lyric_engine` when derived from aligned transcripts.

## Implementation steps (v1)

1. Add DDL helper (`tools/ttc/ttc_schema.py`) and create table `ttc_annotations_v1`.
2. Add CSV/JSON schema docs; stub `data/ttc/ttc_annotations_v1.csv` with headers.
3. Write ingest script for ground-truth corpora (McGill/Harmonix/SALAMI), mapping their IDs to `slug`/`track_id`; record `ttc_source` and `ttc_method`.
4. Wire extractors to read TTC sidecar by slug and emit the `TTC` block in `*.features.json` (no scoring changes).
5. Surface TTC in packs/client outputs when present; keep gated by `STRUCTURE_POLICY.use_ttc`.
6. Optional: LEFT JOIN TTC into Echo/HCI builders for reporting/analytics; do not alter scoring.
7. Future: add `tools/ttc/ttc_estimator.py` (structure/chorus detector, e.g., Essentia/MSAF) writing into the same sidecar with `ttc_source="estimated"` and confidence/version fields.

## Open questions / assumptions

- Ground-truth coverage: which corpus paths are locally available, and how to map their IDs to `tracks.slug`? (Needs mapping table or heuristic matching.)
- Confidence: use a single 0–1 `ttc_confidence` for both annotated and estimated values? (Likely yes, with source-specific calibration notes.)
- Runtime normalization: when `ttc_ratio_runtime` is used, trust `runtime_sec` from TTC sidecar or from audio extractor? (Prefer extractor runtime; sidecar runtime as a cross-check.)
