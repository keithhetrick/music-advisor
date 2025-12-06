import importlib.util
import pytest
import sys
from pathlib import Path

# Ensure builder/export is on sys.path so MusicAdvisor.* imports resolve without env tweaks.
_here = Path(__file__).resolve()
_builder_export = _here.parents[3] / "export"
if str(_builder_export) not in sys.path:
    sys.path.insert(0, str(_builder_export))

# Skip host/engine-dependent tests if required packages are absent.
required_specs = [
    "music_advisor.host.policy",
    "Pipeline.end_to_end",
    "Host.goldilocks",
    "ma_hf_audiotools.Segmentation",
]
missing = []
for spec in required_specs:
    try:
        if importlib.util.find_spec(spec) is None:
            missing.append(spec)
    except ModuleNotFoundError:
        missing.append(spec)

if missing:
    collect_ignore = ["test_advisory_isolation.py", "test_end_to_end_flow.py", "test_goldilocks_policy.py", "test_hf_a12_advisory_isolation.py", "test_hf_a12_kpi.py", "test_hf_a12_ttc_gate.py", "test_kpi.py", "test_regression_hci_invariance.py", "test_ttc_gate.py", "test_ttc_synth_and_gate.py"]
