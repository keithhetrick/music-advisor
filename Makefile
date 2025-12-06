.PHONY: smoke smoke-no-norms calibrate-core freeze-baseline eval-golden eval-negatives
.PHONY: test lint typecheck
.PHONY: check
.PHONY: smoke-audio-engine smoke-lyrics-engine smoke-ttc-engine smoke-host-core smoke-host
.PHONY: run-audio-cli run-lyrics-cli run-ttc-cli run-reco-cli run-advisor-host
.PHONY: install-audio install-lyrics install-ttc install-reco install-host install-host-core
.PHONY: bootstrap-all bootstrap-locked rebuild-venv

# 1) Minimal end-to-end smoke (tone)
smoke:
	python -c 'import math,wave,struct; sr=44100; dur=1.0; f=440.0; n=int(sr*dur); w=wave.open("tone.wav","w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); [w.writeframes(struct.pack("<h", int(0.2*32767*math.sin(2*math.pi*f*i/sr)))) for i in range(n)]; w.close()'
	./automator.sh tone.wav
	@find features_output -name "*.pack.json" -maxdepth 5 | tail -n 1 | xargs -I{} python infra/scripts/pretty.py {}

# 2) Same smoke but without baseline advisory (doesn't change HCI, only messaging)
smoke-no-norms:
	MA_DISABLE_NORMS_ADVISORY=1 ./automator.sh tone.wav
	@find features_output -name "*.pack.json" -maxdepth 5 | tail -n 1 | xargs -I{} python infra/scripts/pretty.py {}

# 3) Run Automator over your calibration core folder
calibrate-core:
	python tools/calibration/calibration_run.py --root "/Volumes/CalibAudio/00_core_modern"

# 4) Aggregate packs into frozen baseline
freeze-baseline:
	python tools/calibration/aggregate_stats.py \
		--packs-root features_output \
		--include "*/*/*/00_core_modern/*/*.pack.json" \
		--include "*/*/*/21_2020_2024/*/*.pack.json" \
		--include "*/*/*/20_2015_2019/*/*.pack.json" \
		--out datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json

# 5) Evaluate your golden set (sanity windowing)
eval-golden:
	python tools/calibration/calibration_run.py --root "/Volumes/CalibAudio/10_golden_set_for_eval"

# 6) Evaluate negatives (sanity: should score low for Pop)
eval-negatives:
	python tools/calibration/calibration_run.py --root "/Volumes/CalibAudio/13_negatives_out_of_domain"
	python tools/calibration/calibration_run.py --root "/Volumes/CalibAudio/14_negatives_novelty_eval"

# Quick QA
test:
	$(PYTHON) $(ORCH) test-all

lint:
	./infra/scripts/with_repo_env.sh -m ruff check hosts/advisor_host engines/recommendation_engine/recommendation_engine

typecheck:
	./infra/scripts/with_repo_env.sh -m mypy --config-file hosts/advisor_host/pyproject.toml hosts/advisor_host

check: lint typecheck test

PYTHON ?= python3
ORCH ?= tools/ma_orchestrator.py

projects:
	$(PYTHON) $(ORCH) list-projects

deps:
	$(PYTHON) $(ORCH) deps

test-project:
	@if [ -z "$(PROJECT)" ]; then echo "usage: make test-project PROJECT=name"; exit 1; fi
	$(PYTHON) $(ORCH) test --project "$(PROJECT)"

test-all-projects:
	$(PYTHON) $(ORCH) test-all

test-affected:
	$(PYTHON) $(ORCH) test-affected

install-projects:
	$(PYTHON) -m pip install -e engines/audio_engine
	$(PYTHON) -m pip install -e engines/lyrics_engine
	$(PYTHON) -m pip install -e engines/ttc_engine
	$(PYTHON) -m pip install -e engines/recommendation_engine
	$(PYTHON) -m pip install -e hosts/advisor_host
	$(PYTHON) -m pip install -e hosts/advisor_host_core

install-audio:
	$(PYTHON) -m pip install -e engines/audio_engine

install-lyrics:
	$(PYTHON) -m pip install -e engines/lyrics_engine

install-ttc:
	$(PYTHON) -m pip install -e engines/ttc_engine

install-reco:
	$(PYTHON) -m pip install -e engines/recommendation_engine

install-host:
	$(PYTHON) -m pip install -e hosts/advisor_host

install-host-core:
	$(PYTHON) -m pip install -e hosts/advisor_host_core

bootstrap-all:
	@test -x .venv/bin/python || python3 -m venv .venv
	. .venv/bin/activate; pip install --upgrade pip
	. .venv/bin/activate; pip install --no-build-isolation -r requirements.txt
	. .venv/bin/activate; pip install --no-build-isolation -e engines/audio_engine -e engines/lyrics_engine -e engines/ttc_engine -e engines/recommendation_engine -e hosts/advisor_host_core -e hosts/advisor_host
	. .venv/bin/activate; python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json
	. .venv/bin/activate; ./infra/scripts/quick_check.sh
	@echo ""
	@echo "[ma] bootstrap complete. Next: run 'python -m ma_helper help' (or alias ma=\"python -m ma_helper\") for helper commands."

bootstrap-locked:
	@test -x .venv/bin/python || python3 -m venv .venv
	. .venv/bin/activate; pip install --upgrade pip
	. .venv/bin/activate; pip install --no-build-isolation -r requirements.lock
	. .venv/bin/activate; pip install --no-build-isolation -e engines/audio_engine -e engines/lyrics_engine -e engines/ttc_engine -e engines/recommendation_engine -e hosts/advisor_host_core -e hosts/advisor_host
	. .venv/bin/activate; python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json
	. .venv/bin/activate; ./infra/scripts/quick_check.sh
	@echo ""
	@echo "[ma] bootstrap complete. Next: run 'python -m ma_helper help' (or alias ma=\"python -m ma_helper\") for helper commands."

hci-smoke:
hci-smoke:
	@if [ -z "$(AUDIO)" ]; then echo "usage: make hci-smoke AUDIO=/path/to/audio" >&2; exit 1; fi
	@echo "[hci-smoke] audio=$(AUDIO)"
	./infra/scripts/smoke_full_chain.sh "$(AUDIO)"

rebuild-venv:
	@read -p "This will remove .venv and recreate it. Continue? [y/N] " ans; \
	  case $$ans in [Yy]*) ;; *) echo "Aborted."; exit 1 ;; esac
	rm -rf .venv
	$(MAKE) bootstrap-all

ci-smoke:
	./infra/scripts/ci_smoke.sh

preflight:
	./infra/scripts/preflight_check.py

# Host-only tests
test-advisor-host:
	$(PYTHON) $(ORCH) test --project advisor_host

test-recommendation-engine:
	$(PYTHON) $(ORCH) test --project recommendation_engine

test-audio-engine:
	$(PYTHON) $(ORCH) test --project audio_engine

test-lyrics-engine:
	$(PYTHON) $(ORCH) test --project lyrics_engine

test-ttc-engine:
	$(PYTHON) $(ORCH) test --project ttc_engine

run-audio-cli:
	$(PYTHON) $(ORCH) run --project audio_engine

run-lyrics-cli:
	$(PYTHON) $(ORCH) run --project lyrics_engine

run-ttc-cli:
	$(PYTHON) $(ORCH) run --project ttc_engine

run-reco-cli:
	$(PYTHON) $(ORCH) run --project recommendation_engine

run-advisor-host:
	$(PYTHON) $(ORCH) run --project advisor_host

quick-check:
	# Prefer PYTHON=.venv/bin/python make quick-check if your system python lacks deps.
	./infra/scripts/quick_check.sh

install-shared:
	pip install -e src/ma_config -e shared

sbom:
	@python -m pip install cyclonedx-bom >/dev/null 2>&1 || true
	@PYTHONPATH=. python -m cyclonedx_py --format json --outfile docs/sbom/sbom.json || echo "cyclonedx_py not available; install with 'python -m pip install cyclonedx-bom'"

vuln-scan:
	@python -m pip install pip-audit >/dev/null 2>&1 || true
	@pip-audit -r requirements.txt || true

clean:
	./infra/scripts/clean_caches.sh

# Deep clean: removes ignored/untracked files. Use CLEAN_FORCE=1 to skip prompt.
deep-clean:
	@if [ "$${CLEAN_FORCE:-0}" != "1" ]; then \
	  read -p "This will run 'git clean -xfd'. Continue? [y/N] " ans; \
	  case $$ans in [Yy]*) ;; *) echo "Aborted."; exit 1 ;; esac; \
	fi
	git clean -xfd

smoke-audio-engine:
	PYTHONPATH=engines/audio_engine/src $(PYTHON) - <<'PY'
		import ma_audio_engine, ma_audio_engine.pipe_cli, ma_audio_engine.extract_cli
		print("audio_engine import ok:", ma_audio_engine.__file__)
	PY

smoke-lyrics-engine:
	PYTHONPATH=engines/lyrics_engine/src $(PYTHON) - <<'PY'
		import ma_lyrics_engine, ma_stt_engine
		print("lyrics_engine import ok:", ma_lyrics_engine.__file__)
		print("stt_engine import ok:", ma_stt_engine.__file__)
	PY

smoke-ttc-engine:
	PYTHONPATH=engines/ttc_engine/src $(PYTHON) - <<'PY'
		import ma_ttc_engine
		print("ttc_engine import ok:", ma_ttc_engine.__file__)
	PY

smoke-host-core:
	PYTHONPATH=hosts/advisor_host_core/src $(PYTHON) - <<'PY'
	import ma_host, ma_host.song_context
	print("host core import ok:", ma_host.__file__)
	PY

smoke-host:
	PYTHONPATH=hosts/advisor_host_core/src:hosts/advisor_host $(PYTHON) - <<'PY'
	import advisor_host.host.advisor as adv
	print("advisor_host import ok:", adv.__file__)
	PY

host-cli-help:
	@PYTHONPATH=hosts/advisor_host_core/src:hosts/advisor_host/src $(PYTHON) hosts/advisor_host/cli/ma_host.py --help

lyrics-cli-help:
	@PYTHONPATH=engines/lyrics_engine/src $(PYTHON) engines/lyrics_engine/tools/lyric_wip_pipeline.py --help

run-chat-host:
	./infra/scripts/run_chat_host.sh

e2e-app-smoke:
	@echo "[e2e] running full app smoke (pipeline + host)"
	./infra/scripts/e2e_app_smoke.sh

build-market-norms:
	@echo "usage: make build-market-norms CSV=/path/to/features.csv REGION=US TIER=StreamingTop200 VERSION=2025-01"
	@if [ -z "$(CSV)" ]; then echo "Set CSV=/path/to/features.csv"; exit 1; fi
	@if [ -z "$(REGION)" ]; then echo "Set REGION=..."; exit 1; fi
	@if [ -z "$(TIER)" ]; then echo "Set TIER=..."; exit 1; fi
	@if [ -z "$(VERSION)" ]; then echo "Set VERSION=..."; exit 1; fi
	python infra/scripts/build_market_norms_snapshot.py --csv "$(CSV)" --region "$(REGION)" --tier "$(TIER)" --version "$(VERSION)" --out data/market_norms

fetch-spotify-playlists:
	@echo "usage: make fetch-spotify-playlists PLAYLISTS=id1,id2 OUT=/tmp/tracks.csv [MAX=500]"
	@if [ -z "$(PLAYLISTS)" ]; then echo "Set PLAYLISTS=comma-separated playlist IDs"; exit 1; fi
	@if [ -z "$(OUT)" ]; then echo "Set OUT=/path/to/output.csv"; exit 1; fi
	SPOTIFY_CLIENT_ID=$$SPOTIFY_CLIENT_ID SPOTIFY_CLIENT_SECRET=$$SPOTIFY_CLIENT_SECRET \
	python infra/scripts/fetch_spotify_playlist_features.py --playlists "$(PLAYLISTS)" --out "$(OUT)" --max-tracks $${MAX:-500}

fetch-billboard-features:
	@echo "usage: make fetch-billboard-features INPUT=path/to/billboard.csv OUT=/tmp/billboard_features.csv"
	@if [ -z "$(INPUT)" ]; then echo "Set INPUT=Billboard CSV with title/artist/year[,spotify_id]"; exit 1; fi
	@if [ -z "$(OUT)" ]; then echo "Set OUT=/path/to/output.csv"; exit 1; fi
	SPOTIFY_CLIENT_ID=$$SPOTIFY_CLIENT_ID SPOTIFY_CLIENT_SECRET=$$SPOTIFY_CLIENT_SECRET \
	python infra/scripts/fetch_billboard_features.py --input "$(INPUT)" --out "$(OUT)"

export-billboard-chart:
	@echo "usage: make export-billboard-chart OUT=/tmp/chart.csv [CHART=hot-100 DATE=YYYY-MM-DD]"
	@if [ -z "$(OUT)" ]; then echo "Set OUT=/path/to/chart.csv"; exit 1; fi
	CHART=$${CHART:-hot-100}; DATE=$${DATE:-}; \
	python infra/scripts/export_billboard_chart.py --chart "$$CHART" $${DATE:+--date $$DATE} --out "$(OUT)"

# Helper: merge client+hci and POST to stub (requires CLIENT, HCI; optional NORMS, SESSION_ID)
chat-analyze:
	@if [ -z "$(CLIENT)" ] || [ -z "$(HCI)" ]; then echo "usage: make chat-analyze CLIENT=... HCI=... [NORMS=...] [SESSION_ID=...]"; exit 1; fi
	@python tools/merge_client_payload.py --client "$(CLIENT)" --hci "$(HCI)" --out /tmp/chat.chat.json
	@python -c "import json, os, pathlib as p; req={'message':'analyze','payload':json.loads(p.Path('/tmp/chat.chat.json').read_text())}; norms=os.getenv('NORMS'); \
norms and req.update({'norms': json.loads(p.Path(norms).read_text())}); \
sid=os.getenv('SESSION_ID'); \
sid and req.update({'session': {'session_id': sid, 'host_profile_id': 'producer_advisor_v1'}}); \
p.Path('/tmp/chat_ready.json').write_text(json.dumps(req), encoding='utf-8'); print('[chat-analyze] wrote /tmp/chat_ready.json')" 
	@curl -s -X POST "$${HOST_URL:-http://localhost:8090/chat}" -H "Content-Type: application/json" --data-binary @/tmp/chat_ready.json | jq .

# Helper: start the local chat stub with auto-kill. Override HOST_PORT/HOST_SESSION_STORE/HOST_SESSION_DIR as needed.
chat-stub:
	@HOST_PORT=$${HOST_PORT:-8090}; \
	HOST_SESSION_STORE=$${HOST_SESSION_STORE:-file}; \
	HOST_SESSION_DIR=$${HOST_SESSION_DIR:-data/sessions}; \
	PYTHONPATH=hosts:engines:engines/recommendation_engine \
	HOST_FORCE_PORT=1 \
	HOST_PORT=$$HOST_PORT \
	HOST_SESSION_STORE=$$HOST_SESSION_STORE \
	HOST_SESSION_DIR=$$HOST_SESSION_DIR \
		.venv/bin/python hosts/advisor_host/cli/http_stub.py

# Helper: start the chat stub using Redis (requires `pip install redis` and a running Redis server)
chat-stub-redis:
	@HOST_PORT=$${HOST_PORT:-8090}; \
	REDIS_URL=$${REDIS_URL:-redis://localhost:6379/0}; \
	if ! python -c "import redis" >/dev/null 2>&1; then \
		echo "redis package not installed; run 'pip install redis' first."; exit 1; \
	fi; \
	PYTHONPATH=hosts:engines:engines/recommendation_engine \
	HOST_FORCE_PORT=1 \
	HOST_PORT=$$HOST_PORT \
	HOST_SESSION_STORE=redis \
	REDIS_URL=$$REDIS_URL \
		.venv/bin/python hosts/advisor_host/cli/http_stub.py

.PHONY: chat-stub-docker
# Dockerized stub + Redis (uses docker/docker-compose.chat-stub.yml)
chat-stub-docker:
	docker-compose -f docker/docker-compose.chat-stub.yml up --build

.PHONY: rec-engine-service
# Run the rec-engine HTTP service locally (serves POST /recommendation)
rec-engine-service:
	@REC_ENGINE_PORT=$${REC_ENGINE_PORT:-8100}; \
	PYTHONPATH=engines:engines/recommendation_engine \\
	.venv/bin/python engines/recommendation_engine/recommendation_engine/service.py

.PHONY: build-dist
# Build sdist/wheel for the root package (helper-friendly metadata refresh).
# If wheel is missing (offline env), fall back to sdist-only; install wheel to get both.
build-dist:
	@if $(PYTHON) -c 'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("wheel") else 1)'; then \
		echo "[build-dist] wheel present; building sdist+wheel (no isolation)"; \
		$(PYTHON) -m build --sdist --wheel . --no-isolation --skip-dependency-check; \
	else \
		echo "[build-dist] wheel missing; building sdist only (install 'wheel' to add wheel build)"; \
		$(PYTHON) -m build --sdist . --no-isolation --skip-dependency-check; \
	fi

refresh-market-norms-monthly:
	@echo "usage: PLAYLISTS=id1,id2 REGION=US TIER=StreamingTop200 VERSION=2025-01 make refresh-market-norms-monthly"
	./infra/scripts/refresh_market_norms_monthly.sh
