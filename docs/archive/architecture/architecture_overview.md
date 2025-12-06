# MusicAdvisor Architecture (Layered & Modular)

This repo is organized into clear tiers with minimal coupling. Each tier can evolve or be replaced without breaking the others.

## Tier 1 — Audio Engine (analysis only)

- **Responsibility:** Compute audio features and axes from audio files. Produces `/audio`-style JSON (tempo_bpm, duration_sec, loudness_LUFS, energy, danceability, valence, axes).
- **Inputs:** Audio files (WAV/MP3).
- **Outputs:** `*.features.json`, `*.merged.json`, sidecars under `features_output/...`.
- **Does NOT:** Pull charts, build norms, or run recommendation logic.
- **Coupling:** None. Downstream consumers read the JSON files only.

## Market Norms (data spine + snapshot builder)

- **Responsibility:** Provide versioned, read-only snapshots of market distributions (tempo, runtime, loudness, energy, danceability, valence, axes).
- **Sources:** UT Billboard research spine (`data/market_norms/market_norms_billboard.db`) plus feature CSVs you generate from analyzed tracks.
- **Tools (file/DB only, no engine/host changes):**
  - `tools/export_billboard_slice.py` (e.g., Q4 Top 40 export).
  - `tools/billboard_checklist.py` (procurement tracking).
  - `tools/missing_features_report.py` (chart vs features gap).
  - `tools/audio_json_to_features_csv.py` (adapter from `/audio` JSON → features CSV).
  - `scripts/build_market_norms_quarter.sh` (snapshot builder wrapper).
  - `tools/show_market_norms_snapshot.py`, `tools/market_norms_db_report.py` (inspection).
  - `tools/export_billboard_top40.py`, `tools/export_billboard_slice.py` (chart slicing).
- **Outputs:** Snapshot JSONs in `data/market_norms/` (e.g., `US_Hot100Top40_2025-Q4.json`).
- **Does NOT:** Touch host or recommendation code; does not require audio engine changes.
- **Coupling:** Recommendation engine _reads_ a snapshot; host can be passed a snapshot path. Nothing else depends on these tools.

## Tier 2 — Recommendation/Optimization Engine

- **Responsibility:** Turn `/audio` payload + optional norms snapshot into a structured recommendation (HCI selection, axes interpretation, historical echo interpretation, optimization list).
- **Inputs:** `/audio` payload from Tier 1; optional market_norms snapshot JSON.
- **Outputs:** Recommendation JSON.
- **Coupling:** None to ingestion; it only _consumes_ a snapshot if provided. Lives in `engines/recommendation_engine/recommendation_engine`. Unchanged by norms/host changes.

## Tier 3 — Host/Chat (thin shell)

- **Responsibility:** Session state, intent routing, formatting replies, UI hints.
- **Inputs:** `/audio` payloads; optional norms snapshot path passed at runtime.
- **Behavior:** Calls recommendation engine; if no norms snapshot, uses advisory-only path and surfaces a warning.
- **Does NOT:** Compute norms, charts, or audio features. No domain logic beyond formatting.
- **Coupling:** Consumes recommendation outputs; optional snapshot is passed in. Lives in `hosts/advisor_host`.

## Optional Helpers (safe to move or replace)

- `tools/make_client_bundle.py` (combine audio + recommendation JSON for clients).
- Checklists, missing-reports, DB coverage reports, snapshot inspectors — all file-based and optional.

## Data Flow (end-to-end, replaceable at each step)

1. **Analyze audio** (Tier 1) → `/audio` JSONs in `features_output/...`.
2. **(Optional) Market norms build**: chart export + features CSV → `build_market_norms_snapshot.py` → snapshot JSON.
3. **Recommendation** (Tier 2): `/audio` + snapshot → recommendation JSON.
4. **Host** (Tier 3): receives payload + optional snapshot; formats replies; warns if no snapshot.

Each arrow is a file/API boundary. You can swap any component (e.g., a licensed norms feed, a different host, or a different audio engine) as long as it produces/consumes the same payload shapes. No tier hard-depends on the internal code of another.

## Appendix: Engine Artifacts and Consumers

- `*.features.json` (Tier 1): Core audio features (tempo/duration/LUFS/energy/danceability/valence, plus metadata).
  - Consumed by: norms adapter (`tools/audio_json_to_features_csv.py`), rec engine (when shaped as `/audio`), and indirectly by hosts via merged/client payloads.
- `*.merged.json` (Tier 1): Features plus merged metadata (source_audio name, etc.).
  - Consumed by: norms adapter, rec engine inputs (if used as `/audio`), bundle maker, downstream tooling.
- `*.hci.json`, `*.neighbors.json`, `*.ttc.json`, sidecars: Additional analysis outputs.
  - Not required by norms builder; rec engine will use HCI/echo fields if present in the `/audio` payload.
- `*.client.json`, `*.client.rich.txt`: Host-facing render data.
  - Optional; used by host/clients, not by norms builder or rec engine logic.
- `run_summary.json`: Execution summary/logging.
  - Informational only.

Only `/audio`-shaped payloads (features/merged with optional HCI/axes/echo) are required by the rec engine; the norms builder only needs numeric feature columns via the adapter. Other artifacts are optional and do not couple tiers.
