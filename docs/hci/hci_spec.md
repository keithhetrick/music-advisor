# HCI Spec (Canonical)

Merged view of HCI_v1.x (audio-first Echo architecture), calibration semantics, ranking, and client-context helpers. Full legacy texts live in `docs/archive/hci/`.

## Scope & philosophy

- **Status:** HCI_v1.2 draft (Echo-first) with ModernScore overlay; Lyric Engine is future-facing but mirrors audio roles.
- **Principle:** “The Top 40 is the Top 40 of 40 years ago.” EchoScore measures how deeply a song sits inside proven hit DNA; ModernScore is a separated overlay.
- **Boundaries:** Audio engine emits stable JSON; host never recomputes scores. Keep contracts shape-stable.

## Roles & responsibilities (from HCI_v1.2 spec)

- **Audio Intelligence Engine**
  - Compute six axes from `features_full`: TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence.
  - Derive EchoScore_audio_raw → calibrated EchoScore_audio via frozen benchmark corpus.
  - Derive ModernScore_audio_raw → calibrated ModernScore_audio vs modern-only slice.
  - Optionally expose percentiles for both.
- **Lyric Intelligence Engine (planned)**
  - Mirror the above for lyrics: six lyric axes, EchoScore_lyric, ModernScore_lyric, percentiles, stable JSON schema.
- **Host**
  - Consumes `/audio` payload + optional norms snapshot; formats replies and warnings; does not change scores.

## Calibration & semantics (from HCI_v1 calibration notes)

- Cohort-relative, structural/emotional score on a 0–1 scale anchored to a frozen market baseline (e.g., US Pop 2025Q4). It is not a universal “goodness” score.
- Inputs must include bpm, duration_sec, loudness_lufs, energy, danceability, valence; Gaussian fits are used for tempo/runtime/loudness axes.
- Baseline (`calibration/market_norms_us_pop.json` copied from `datahub/cohorts/...`) defines means/σ for Tempo/Runtime/Loudness fits.
- Keep Trend/advisory layers off during calibration; ModernScore overlay is kept separate from EchoScore.
- HCI_v1 answers: “How strongly does this track sit in the current sweet-spot of those six axes for this cohort?”

## Ranking (operational)

Rank `.hci.json` within a folder:

```bash
python tools/hci_rank_from_folder.py \
  --root features_output/2025/11/25 \
  --out /tmp/hci_rank_summary.txt \
  --csv-out /tmp/hci_rank.csv \
  --markdown-out /tmp/hci_rank.md
```

- Filters: `--tiers WIP-A+,WIP-A` to limit tiers (default: all).
- Outputs: summary text + optional CSV/Markdown with score/raw/tier/title; includes stats (max/min/median) and tier counts.
- `score` = `HCI_v1_final_score` (audio historical echo diagnostic; not a hit predictor).

## Client rich context injection (operational)

Inject HCI+Historical Echo header into `.client.rich.txt`:

```bash
python tools/hci/ma_add_echo_to_client_rich_v1.py \
  --root features_output/2025/11/25/Some Track \
  --skip-existing \
  --verbose
```

- Uses sibling `.features.json` + `.hci.json`; dedupes tiers (prefers Tier1) and shows neighbor summary. `--skip-existing` avoids rewrites; `--verbose` logs per file.
- Header captures structure policy, Goldilocks/HCI policy summary, context (region/profile/audio_name), HCI summary, pipeline QA fields, and historical-echo neighbors.

## How to read HCI + neighbors (annotated)

`.hci.json` (truncated):

```json
{
  "audio_axes": [0.83, 0.78, 0.74, 0.71, 0.68, 0.42],
  "hci_score": { "raw": 0.64, "calibrated": 0.61, "final": 0.61 },
  "historical_echo_v1": {
    "primary_decade": "1990s",
    "closest": [{ "title": "Example", "score": 0.81, "decade": "1990s" }]
  },
  "feature_pipeline_meta": {
    "tempo_backend_detail": "essentia",
    "sidecar_status": "ok"
  }
}
```

- `audio_axes` order: TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence.
- `hci_score.final` is the calibrated diagnostic; `raw` is pre-calibration.
- `historical_echo_v1` lists nearest historical neighbors and primary decade.
- `feature_pipeline_meta` records sidecar/backend provenance.

`.neighbors.json` (truncated):

```json
{
  "neighbors": [
    {
      "title": "Neighbor Song",
      "artist": "Artist",
      "score": 0.79,
      "decade": "2000s",
      "tier": "tier1_modern"
    }
  ],
  "meta": { "top_k": 25, "tier_filter": ["tier1_modern", "tier2_modern"] }
}
```

- Use `neighbors` to render a “closest songs” card; `meta` shows filters used.
- Scores are similarity measures; higher = closer in historical echo space.

### Field reference (common keys)

- `audio_axes` — order: TempoFit, RuntimeFit, LoudnessFit, Energy, Danceability, Valence.
- `hci_score.raw` / `.calibrated` / `.final` — raw vs calibrated vs final diagnostic score.
- `historical_echo_v1.primary_decade` — dominant decade for echo match.
- `historical_echo_v1.closest` — top neighbors with scores/decades (deduped by tier).
- `neighbors` — full neighbor list; `meta.top_k` and `meta.tier_filter` show the filters applied.
- `feature_pipeline_meta` — provenance (tempo backend, sidecar status, config hash if present).
- Schemas: `docs/schemas/hci.schema.json`, `docs/schemas/neighbors.schema.json`.

### What to surface in UI

- Show HCI final score and axes chart (use `audio_axes` ordering above).
- Show primary decade and a few top `historical_echo_v1.closest` entries.
- If norms snapshot absent, badge advisory-only; if present, badge `market_norms_used` (from host response).
- Use `neighbors` to render a “similar songs” list; respect `meta.top_k`/`tier_filter`.

JSON Schemas: `docs/schemas/hci.schema.json`, `docs/schemas/neighbors.schema.json`.

## Valence axis notes (v2 draft)

- Valence axis guidance remains the same pipeline surface (0–1) but leans on normalized lyrical/affective markers; keep calibration cohorts explicit.
- See archived `Valence_Axis_HCI_v2.md` for deeper methodology while v2 is finalized.

## Where to go next

- Run commands: `docs/ops/commands.md`.
- Payload/schema references: `docs/EXTRACT_PAYLOADS.md`, `docs/pipeline/README_ma_audio_features.md`.
- Archived full texts: `docs/archive/hci/` (original spec, calibration notes, ranking cheat, client-context guide, valence axis draft).
