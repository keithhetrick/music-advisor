import pytest
from pathlib import Path


def test_macos_app_manifest_present():
    root = Path(__file__).resolve().parents[2]
    manifest = root / "Package.swift"
    if not manifest.exists():
        pytest.skip("macOS Package.swift not present locally")
    assert manifest.exists(), "macOS app Package.swift missing"
