# MusicAdvisor — TTC/Policy Contract Quickstart

This repo enforces the v1 contract:

- **Numeric HCI_v1** is computed from **audio axes** and capped by **host policy only**.
- **Structural policy** (TTC gate, exposures) may drop/add **subfeatures** (e.g., `chorus_lift`) but **never changes HCI numbers**.
- **Goldilocks** is advisory-only (market/emotional deltas); it **never mutates HCI**.

## Quick runs

### 1) Install (editable) + tests

Use your outer repo’s virtualenv; the vendored .venv is not required.

```bash
# from music-advisor root with .venv active
pip install --no-build-isolation -e vendor/MusicAdvisor_BuilderPack/builder/export/MusicAdvisor
pip install -U pytest  # if you want to run tests here
pytest -q
# or: pip install --no-build-isolation -r vendor/MusicAdvisor_BuilderPack/builder/export/MusicAdvisor/requirements.txt
# for pinned tooling: pip install --no-build-isolation -r vendor/MusicAdvisor_BuilderPack/builder/export/MusicAdvisor/requirements-dev.txt
```

### 2) Local smoke (outside GPT)

```bash
music-advisor-smoke payload.json --market 0.48 --emotional 0.67 --round 3
```

Expected: JSON with `HCI_v1.score/raw`, `Baseline.MARKET_NORMS`, and advisory blocks (Goldilocks, Structural, TTC_Gate). If `payload.json` is missing fields, HCI will still return but advisory may note gaps.

Sample payload: `Examples/sample_payload_minimal.json` (flat axes + TTC stub). Swap in your extractor output to mirror end-to-end behavior.

### 3) Packs + helpers (GPT/client-rich)

- `music-advisor from-pack --pack <path>.pack.json --client <path>.client.rich.txt` (preferred) or `--client <path>.client.txt`.
- `--client AUTO` will auto-pick a helper next to the pack, preferring `*.client.rich.txt` when present.

Common failures & fixes

- Missing Baseline/profile: ensure MARKET_NORMS.profile is set in payload or active baseline files are in place.
- Null HCI_v1: check that `audio_axes` has 6 floats and payload parses.
- Empty advisory blocks: payload missing TTC/STRUCTURE fields; add TTC stub or verify policy config.
- Pack ingest fails: ensure pack JSON has MARKET_NORMS.profile and required meta; run schema validation if available.
