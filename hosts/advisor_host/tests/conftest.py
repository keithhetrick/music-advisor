import sys
from pathlib import Path

# Ensure repository root is on sys.path for editable/dev runs without install
# NOTE: parents indices from this file:
# 0 = file, 1 = tests/, 2 = advisor_host/, 3 = hosts/, 4 = repo root
FILE = Path(__file__).resolve()
ROOT_ADVISOR_HOST = FILE.parents[1]
ROOT_HOSTS = FILE.parents[2]
ROOT_REPO = FILE.parents[3]
VENDOR = ROOT_REPO / "vendor"
ENGINES = ROOT_REPO / "engines"
REC_ENGINE_SRC = ENGINES / "recommendation_engine"

for p in (ROOT_ADVISOR_HOST, ROOT_HOSTS, ROOT_REPO, VENDOR, ENGINES, REC_ENGINE_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
