# HitCheck — v1.0 Prototype (Music Advisor v1.1.1)

**Purpose**: Benchmark a WIP/original against the **2024 Hit List Blueprint (US_Pop_2025 Midtempo ~100 BPM)** without modifying **HCI_v1**. Outputs **nearest neighbors**, **axis drift mapping**, **echo lineage**, and **HCI_v1p** (projection).

Install (outer env, once):

```bash
pip install --no-build-isolation -e vendor/MusicAdvisor_BuilderPack/builder/export/MusicAdvisor
```

## Commands (manual trigger)

```shell
/hitcheck init [k=8 metric=cosine alpha=0.12 lambda=0.08]
/hitcheck run
/hitcheck export summary
/hitcheck export full
```

Quick run expectation:
- `/hitcheck init` ACKs config and builds/loads index.
- `/hitcheck run` returns neighbors and drift deltas.
- `/hitcheck export summary` includes HCI_v1 (neutral) and HCI_v1p (projection); HCI_v1p should not be null.

Smoketest guidance:
- Ensure `hitcheck/config.yaml` paths point to an available cohort (index.npz + features.csv + meta.json). For a lightweight check, build a tiny index from a small CSV via `scripts/build_hitcheck_index.py` with reduced k.
- Healthy output: non-empty neighbors list; drift table populated; HCI_v1p differs modestly from HCI_v1 (projection).
- If neighbors are empty or HCI_v1p null, rebuild the index or check that feature columns match the config schema.
- This bundle ships with a tiny synthetic cohort at `MusicAdvisor/Data/HitCheck_Cohorts/Blueprint_US_Pop_2025_midtempo_v1_1/` referenced by the default config for offline smoke.

## Pipeline

`import → normalize → kNN → drift → lineage → HCI_v1p → export`

- **HCI_v1**: stays neutral (from Advisor).
- **HCI_v1p**: contextual projection (neighbors ± drift penalty).

## Config

- `config.yaml` sets paths (reference features/index), thresholds, and defaults.
- Build (or rebuild) the reference index with:

```shell
python -m MusicAdvisor.HitCheck.scripts.build_hitcheck_index
--cfg MusicAdvisor/HitCheck/hitcheck/config.yaml
```

Expected: neighbors + drift table + `HCI_v1` (neutral) and `HCI_v1p` (projection). If you see missing refs, rebuild the index.

Troubleshooting cues
- If neighbors are empty: reference index missing/stale → rebuild.
- If HCI_v1p is null: projection failed → check input features match config schema.

## Integration

- Commands are wired via `MusicAdvisor/Advisor/commands/hitcheck_commands.py`.
- Router patch: `MusicAdvisor/Router/Router_HitCheck.patch.yaml`.
