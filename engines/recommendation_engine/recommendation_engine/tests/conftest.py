import sys
from pathlib import Path

# Ensure repository root on sys.path for editable/dev runs without install
# parents indices from this file:
# 0=file, 1=tests/, 2=recommendation_engine package, 3=recommendation_engine project root,
# 4=engines/, 5=repo root
ROOT_REPO = Path(__file__).resolve().parents[5]
if str(ROOT_REPO) not in sys.path:
    sys.path.insert(0, str(ROOT_REPO))
