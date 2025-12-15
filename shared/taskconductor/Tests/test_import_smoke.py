import pytest
from pathlib import Path


def test_taskconductor_sources_present():
    root = Path(__file__).resolve().parents[2]
    sources = root / "Sources"
    manifest = root / "Package.swift"
    if not sources.exists() or not manifest.exists():
        pytest.skip("TaskConductor Sources/Package.swift not present locally")
    assert sources.exists(), "TaskConductor Sources path missing"
    assert manifest.exists(), "Swift Package.swift not found for TaskConductor"
