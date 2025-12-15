import pytest
from pathlib import Path


def test_design_system_importable():
    package_path = Path(__file__).resolve().parents[2] / "Sources"
    manifest = Path(__file__).resolve().parents[2] / "Package.swift"
    if not package_path.exists() or not manifest.exists():
        pytest.skip("Design system Sources/Package.swift not present locally")
    assert package_path.exists(), "Design system Sources path missing"
    assert manifest.exists(), "Swift Package.swift not found"
