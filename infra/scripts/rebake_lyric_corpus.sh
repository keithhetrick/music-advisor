#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

DB="${1:-${LYRIC_INTEL_DB:-data/lyric_intel/lyric_intel.db}}"
LEXICON="${2:-data/external/concreteness/brysbaert_concreteness_lexicon.csv}"
CALIB="${3:-${LYRIC_LCI_CALIBRATION:-shared/calibration/lci_calibration_us_pop_v1.json}}"
NORMS="${4:-${LYRIC_LCI_NORMS_PATH:-shared/calibration/lci_norms_us_pop_v1.json}}"

python_cmd="${PYTHON:-${repo_root}/.venv/bin/python3}"

"${python_cmd}" -m tools.lyric_intel_engine phase2-features --db "${DB}" --concreteness-lexicon "${LEXICON}"
"${python_cmd}" -m tools.lci_index_builder score-songs --db "${DB}" --calibration "${CALIB}" --profile lci_us_pop_v1
"${python_cmd}" -m tools.lyric_lci_norms --db "${DB}" --profile lci_us_pop_v1 --out "${NORMS}"
