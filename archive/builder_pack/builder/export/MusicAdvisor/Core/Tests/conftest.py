import importlib.util
import pytest
import sys
from pathlib import Path

# Ensure builder/export is on sys.path so MusicAdvisor.* imports resolve without env tweaks.
_here = Path(__file__).resolve()
_builder_export = _here.parents[4] / "export"
if str(_builder_export) not in sys.path:
    sys.path.insert(0, str(_builder_export))

# Skip host-dependent tests if the host package is not available in this environment.
try:
    spec = importlib.util.find_spec("music_advisor.host.policy")
except ModuleNotFoundError:
    spec = None

collect_ignore = []
if spec is None:
    collect_ignore.append("test_policies_do_not_change_hci.py")
