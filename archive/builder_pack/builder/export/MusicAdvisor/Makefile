.PHONY: install test smoke advisor lint check test-smoke clean
PY ?= python3
PIP ?= $(PY) -m pip

install:
	$(PIP) install -e .
	$(PIP) install -r requirements.txt

test:
	$(PY) -m pytest -q

smoke:
	music-advisor-smoke payload.json --market 0.48 --emotional 0.67 --round 3

advisor:
	music-advisor from-pack --pack mock_pack.json --client mock_client.txt --print-audit --round 3

hitcheck-smoke:
	# Uses bundled synthetic cohort in hitcheck/config.yaml
	python -m MusicAdvisor.HitCheck.scripts.build_hitcheck_index --cfg MusicAdvisor/HitCheck/hitcheck/config.yaml
	# Load the index to ensure it is readable and has rows
	$(PY) - <<'PY'
import numpy as np
from pathlib import Path
cfg = Path("MusicAdvisor/HitCheck/hitcheck/config.yaml")
import yaml
d = yaml.safe_load(cfg.read_text())
idx = Path(d["paths"]["index_npz"])
arr = np.load(idx, allow_pickle=True)
X = arr["X_ref"]
meta = arr["meta"]
assert X.shape[0] > 0, "HitCheck index has no rows"
assert meta.size == X.shape[0], "Meta rows do not match X_ref rows"
print("[OK] HitCheck index loaded:", idx, "rows:", X.shape[0])
PY

test-smoke:
	music-advisor-smoke Examples/sample_payload_minimal.json --market 0.48 --emotional 0.67 --round 3

lint:
	$(PIP) check

check:
	$(PY) -m compileall MusicAdvisor || true

clean:
	rm -rf build dist *.egg-info
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
