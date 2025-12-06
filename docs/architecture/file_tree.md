# File Tree (Current Modular Layout)

Reference guide to the active, modular layout. No entry-point paths were moved to avoid breaking automators; new “home” locations are called out for future migrations.

```text
.
├── adapters/                 # Adapter layer (swappable components)
│   ├── backend_registry.py   # Tempo/key backends registry (librosa/essentia/madmom)
│   ├── cache_adapter.py      # Cache backend selection (noop/fs) + config/cache.json
│   ├── confidence_adapter.py # Tempo confidence mapping (config/tempo_confidence.json)
│   ├── hash_adapter.py       # Hash algorithm selection (config/hash.json)
│   ├── logging_adapter.py    # Logging defaults from config/logging.json
│   ├── qa_policy_adapter.py  # QA presets/policies (config/qa_policy.json)
│   └── audio_loader_adapter.py # Audio loader/mono merge (config/audio_loader.json)
├── config/                   # Optional overrides (safe defaults baked into code)
│   ├── *.json.example        # Examples for backend, tempo confidence, QA, logging, cache, hash, audio loader
│   └── README.md             # How to use the optional configs
├── docs/
│   ├── architecture/         # Architecture + modularity docs
│   │   └── file_tree.md      # This file
│   ├── tempo_conf_calibration.md
│   └── modularity_map.md     # Adapter matrix and config knobs
├── pipelines/                # Canonical pipeline entry wrappers (mirrors scripts/)
│   ├── automator.sh
│   ├── automator_full.sh
│   ├── run_full_pipeline.sh
│   ├── run_extract_strict.sh
│   ├── run_echo_inject_guardrails.sh
│   ├── run_rank_with_guardrails.sh
│   └── qa_automator_probe.sh
├── scripts/
│   ├── guardrails/           # Guardrail wrappers + README
│   ├── README.md
│   └── *.sh                  # Legacy script locations (kept for compatibility)
├── tools/                    # Main CLI tools (entry points remain here)
│   ├── ma_audio_features.py  # Extractor; imports adapters & configs
│   ├── cli/tempo_sidecar_runner.py # Sidecar runner (essentia/madmom/librosa; shim at tools/tempo_sidecar_runner.py)
│   ├── ma_add_echo_to_*      # Injectors
│   ├── hci_rank_from_folder.py
│   └── backfill_features_meta.py
├── vendor/                   # External assets / host builder
├── README.md                 # Top-level run + architecture pointers
├── docs/pipeline/README_ma_audio_features.md # Extractor/sidecar details
└── COMMANDS.md               # Quick-start commands; points to pipelines/ & scripts/
```

## What’s modular today

- Backends: swap tempo/key providers via `adapters/backend_registry.py` + `config/backend.json`.
- Tempo confidence: map/normalize external scores via `adapters/confidence_adapter.py` + `config/tempo_confidence.json`.
- Cache: choose fs/noop via `adapters/cache_adapter.py` + `config/cache.json`.
- Hashing: configure algorithm/chunk via `adapters/hash_adapter.py` + `config/hash.json`.
- Audio loading: force backend/mono merge via `adapters/audio_loader_adapter.py` + `config/audio_loader.json`.
- QA/logging: presets in `config/qa_policy.json` and `config/logging.json`.
- Pipelines: use `pipelines/*.sh` (or legacy `scripts/*.sh`) for end-to-end runs.

### Migration guidance (future-proofing)

- Keep entry-point CLIs in `tools/` but import shared logic from `adapters/` and future `src/` helpers.
- Add new adapters under `adapters/` with a matching `config/<name>.json` example and a doc blurb in `modularity_map.md`.
- When moving or renaming scripts, add a thin wrapper in `scripts/` to preserve backwards compatibility.
